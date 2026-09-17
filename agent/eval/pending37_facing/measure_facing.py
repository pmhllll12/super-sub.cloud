#!/usr/bin/env python3
"""**방향을 판별할 수 있는가** — 처방 (나)의 전제 (미결 `ho` 37번 3회차).

    uv run python eval/pending37_facing/measure_facing.py    # GPU 불필요

1·2회차로 결함의 크기(인스텝 최종 등급 44% 변동)와 구조(투구는 2등급 구간
전체가 Δ=2)는 다 나왔다. 남은 것은 처방 선택이고, (나) **방향 인식 지표**가
원인에 가깝다. 그런데 (나)에는 전제가 있다 — **어느 쪽을 보는지 알아낼 수
있어야 한다.** 못 알아내면 (나)는 죽고 (가)가 기본값이 된다.

🔴 **코 오프셋은 후보에서 뺐다 — 구조적 순환이다.** 부호를 정하려는 값이
`shoulder_c - hip_c` 인데 앞으로 기울면 코도 같은 방향으로 간다. 그 큐로
부호를 정하면 `trunk_lean` 이 **항상 양수**가 되어 지표가 통째로 죽는다.
얼굴 **좌표**를 쓰는 큐는 전부 같은 사유로 뺀다.

남은 두 큐는 `trunk` 벡터를 입력으로 쓰지 않는다:

    큐 1  귀·눈 **신뢰도** 비대칭   — 좌표를 안 쓴다. 가림만 본다
    큐 2  골반중심 x **변위**       — 자세가 아니라 위치의 변화다

규격은 `PREREGISTRATION.md`(커밋 `b1fba98`, 코드보다 먼저).

🔴 **`features.py` 를 고치지 않는다. 방향 인식을 구현하지 않는다** — 구현은
별도 회차이고 B-6 재실행을 부른다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.features import (  # noqa: E402
    L_HIP,
    L_SHOULDER,
    R_HIP,
    R_SHOULDER,
    normalization_params,
)

CACHE = ROOT / "eval" / "phaseA" / "cache_target30"

# COCO-17 — features.py 가 이름을 안 붙인 얼굴 관절. 🔴 **신뢰도만** 쓴다.
L_EYE, R_EYE = 1, 2
L_EAR, R_EAR = 3, 4

# --- 🔴 사전 등록 문턱 — 데이터를 보기 전에 박았다 -------------------------
CONF_GAP = 0.2      # 가시성 판별: |Δconf| 가 이 이상
MOVE_GAP = 0.5      # 이동 판별: |Δx| 가 이 이상 (어깨너비 배수)
STABLE = 0.80       # 시간 안정: 유효 프레임의 이 비율이 한 부호
COVERAGE_BAR = 0.70  # 기준 A
AGREE_BAR = 0.70     # 기준 B
STABLE_BAR = 0.80    # 기준 C
SMALL_N = 10         # 분모가 이 아래면 비율을 내지 않는다


def load(path: Path):
    d = np.load(path)
    return d["keypoints"]


def visibility_cue(kps: np.ndarray, left: int, right: int):
    """큐 1 — 좌우 얼굴 관절의 **신뢰도 차**. 🔴 좌표를 안 쓴다.

    반환: (부호, 판별된 프레임 수, 안정성). 부호 0 은 판별 불가.
    """
    cl, cr = kps[:, left, 2], kps[:, right, 2]
    ok = (cl > 0) & (cr > 0)
    if not ok.any():
        return 0, 0, 0.0
    diff = cl[ok] - cr[ok]
    decided = np.abs(diff) >= CONF_GAP
    n = int(decided.sum())
    if n == 0:
        return 0, 0, 0.0
    signs = np.sign(diff[decided])
    pos = float((signs > 0).mean())
    stability = max(pos, 1.0 - pos)
    return (1 if pos >= 0.5 else -1), n, stability


def movement_cue(kps: np.ndarray):
    """큐 2 — 골반중심 x 의 변위. 🔴 자세가 아니라 **위치**다.

    `normalization_params` 로 어깨너비 스케일을 얻어 정규화 단위로 만든다.
    """
    conf_ok = (kps[:, [L_HIP, R_HIP], 2] > 0).all(axis=1)
    if conf_ok.sum() < 2:
        return 0, 0.0
    hip_c = (kps[:, L_HIP, :2] + kps[:, R_HIP, :2]) / 2.0
    _center, scale = normalization_params(kps)
    s = float(np.nanmedian(scale)) if np.ndim(scale) else float(scale)
    if not np.isfinite(s) or s <= 0:
        return 0, 0.0
    idx = np.flatnonzero(conf_ok)
    delta = float(hip_c[idx[-1], 0] - hip_c[idx[0], 0]) / s
    if abs(delta) < MOVE_GAP:
        return 0, delta
    return (1 if delta > 0 else -1), delta


def trunk_sign(kps: np.ndarray):
    """관찰용 — `trunk_lean` 의 부호. 🔴 **큐가 아니다.** 대조로만 쓴다."""
    ok = (kps[:, [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP], 2] > 0).all(axis=1)
    if not ok.any():
        return 0
    sh = (kps[:, L_SHOULDER, :2] + kps[:, R_SHOULDER, :2]) / 2.0
    hp = (kps[:, L_HIP, :2] + kps[:, R_HIP, :2]) / 2.0
    dx = float(np.nanmedian((sh - hp)[ok, 0]))
    return 1 if dx > 0 else (-1 if dx < 0 else 0)


def main() -> None:
    paths = sorted(CACHE.glob("*.npz"))
    if not paths:
        raise SystemExit(f"🔴 캐시를 찾을 수 없다: {CACHE}")

    rows = []
    for p in paths:
        kps = load(p)
        ear, ear_n, ear_stab = visibility_cue(kps, L_EAR, R_EAR)
        eye, eye_n, eye_stab = visibility_cue(kps, L_EYE, R_EYE)
        move, delta = movement_cue(kps)
        rows.append({
            "clip": p.stem, "ear": ear, "ear_n": ear_n, "ear_stab": ear_stab,
            "eye": eye, "eye_n": eye_n, "eye_stab": eye_stab,
            "move": move, "delta": delta, "trunk": trunk_sign(kps),
        })

    n = len(rows)
    print("═" * 96)
    print(f"방향 판별 — {n}클립 (cache_target30) · ⚠️ **전부 야구 타격이다**")
    print("═" * 96)
    print(f"  문턱(사전 등록): 가시성 |Δconf| ≥ {CONF_GAP} · "
          f"이동 |Δx| ≥ {MOVE_GAP} 어깨너비 · 안정 {STABLE:.0%}")

    def coverage(key):
        return sum(1 for r in rows if r[key] != 0)

    print("\n" + "═" * 96)
    print("커버리지 — 큐별로 **따로** 적는다 (하나만 되면 그것만 쓰면 된다)")
    print("═" * 96)
    print(f"  {'큐':28s} │ {'판별된 클립':>12s} │ 비율")
    cov = {}
    for key, label in (("ear", "큐 1a 귀 신뢰도 비대칭"),
                       ("eye", "큐 1b 눈 신뢰도 비대칭"),
                       ("move", "큐 2  골반중심 x 변위")):
        c = coverage(key)
        cov[key] = c / n
        mark = " ✅" if c / n >= COVERAGE_BAR else " 🔴"
        print(f"  {label:28s} │ {c:9d}/{n:2d} │ {c / n:5.0%}{mark}")

    print("\n" + "═" * 96)
    print("시간 안정 — 판별된 클립 중 한 부호가 80%+ 인 비율")
    print("═" * 96)
    for key, skey, label in (("ear", "ear_stab", "큐 1a 귀"),
                             ("eye", "eye_stab", "큐 1b 눈")):
        dec = [r for r in rows if r[key] != 0]
        if not dec:
            print(f"  {label:12s} 판별된 클립이 없다")
            continue
        st = sum(1 for r in dec if r[skey] >= STABLE)
        small = len(dec) < SMALL_N
        txt = f"{st}/{len(dec)}" if small else f"{st}/{len(dec)} ({st / len(dec):.0%})"
        print(f"  {label:12s} {txt}"
              + ("   ⚠️ 분모가 한 자릿수 — 비율을 내지 않는다" if small else ""))
    print("  큐 2         이동은 클립 단위 변위라 **시간 안정 개념이 없다**")

    print("\n" + "═" * 96)
    print("일치 — 둘 다 판별을 낸 클립에서 부호가 같은가")
    print("═" * 96)
    pairs = (("ear", "eye", "귀 ↔ 눈  ⚠️ 둘 다 얼굴이라 완전 독립이 아니다"),
             ("ear", "move", "귀 ↔ 이동  ← 🔴 **이것이 독립 대조다**"),
             ("eye", "move", "눈 ↔ 이동"))
    agree = {}
    for a, b, label in pairs:
        both = [r for r in rows if r[a] != 0 and r[b] != 0]
        if not both:
            print(f"  {label:44s} 둘 다 판별된 클립이 **0** — 대조 불가")
            agree[(a, b)] = None
            continue
        same = sum(1 for r in both if r[a] == r[b])
        small = len(both) < SMALL_N
        agree[(a, b)] = same / len(both)
        txt = f"{same}/{len(both)}" if small else \
              f"{same}/{len(both)} ({same / len(both):.0%})"
        print(f"  {label:44s} {txt}"
              + ("   ⚠️ 분모가 한 자릿수 — 판정하지 않는다" if small else ""))

    print("\n" + "═" * 96)
    print("관찰 (판정에 쓰지 않는다) — 큐와 `trunk_lean` 부호의 일치율")
    print("═" * 96)
    print("  🔴 높다고 순환이 아니다 — 실제로 대부분 앞으로 기울면 정당하게")
    print("     높다. 구조적 비순환은 기준 D 가 본다.")
    for key, label in (("ear", "귀"), ("eye", "눈"), ("move", "이동")):
        both = [r for r in rows if r[key] != 0 and r["trunk"] != 0]
        if not both:
            print(f"  {label:6s} 대조 가능한 클립 0")
            continue
        same = sum(1 for r in both if r[key] == r["trunk"])
        print(f"  {label:6s} {same}/{len(both)}")

    # --- 판별이 안 된 사유 ----------------------------------------------
    print("\n" + "═" * 96)
    print("판별이 안 된 사유 — 신뢰도가 낮아서인가, 차이가 작아서인가")
    print("═" * 96)
    for key, nkey, label in (("ear", "ear_n", "귀"), ("eye", "eye_n", "눈")):
        undecided = [r for r in rows if r[key] == 0]
        zero_frames = sum(1 for r in undecided if r[nkey] == 0)
        print(f"  {label}: 판별 실패 {len(undecided)}클립 — "
              f"문턱을 넘는 프레임이 **0개**인 클립 {zero_frames}개")
    nomove = [r for r in rows if r["move"] == 0]
    if nomove:
        med = float(np.median([abs(r["delta"]) for r in nomove]))
        print(f"  이동: 판별 실패 {len(nomove)}클립 — 변위 중앙 "
              f"**{med:.2f} 어깨너비** (문턱 {MOVE_GAP})")

    # --- 기준 -----------------------------------------------------------
    best_cov = max(cov.values())
    a_ok = best_cov >= COVERAGE_BAR
    em = agree.get(("ear", "move"))
    both_em = [r for r in rows if r["ear"] != 0 and r["move"] != 0]
    b_ok = em is not None and em >= AGREE_BAR and len(both_em) >= SMALL_N
    dec_ear = [r for r in rows if r["ear"] != 0]
    c_ok = bool(dec_ear) and \
        sum(1 for r in dec_ear if r["ear_stab"] >= STABLE) / len(dec_ear) >= STABLE_BAR

    print("\n" + "═" * 96)
    print("사전 등록 기준 (커밋 `b1fba98` — 결과를 보고 바꾸지 않았다)")
    print("═" * 96)
    print(f"  A 커버리지 — 한 큐가 70%+ ……………………… "
          f"{'✅ 만족' if a_ok else '🔴 불만족'}   (최고 {best_cov:.0%})")
    if em is None or len(both_em) < SMALL_N:
        print(f"  B 일치 — 귀↔이동 70%+ ……………………… "
              f"⚠️ **판정하지 않는다** (분모 {len(both_em)})")
    else:
        print(f"  B 일치 — 귀↔이동 70%+ ……………………… "
              f"{'✅ 만족' if b_ok else '🔴 불만족'}   ({em:.0%})")
    print(f"  C 시간 안정 80%+ ……………………………………… "
          f"{'✅ 만족' if c_ok else '🔴 불만족'}")
    print("  D 구조적 비순환 ……………………………………… ✅ 두 큐 어느 것도")
    print("     어깨중심·골반중심의 좌표차를 입력으로 쓰지 않는다 (신뢰도 · 위치변위)")

    print("\n" + "═" * 96)
    # 🔴 사전 등록은 「(나)가 살아 있는가」에 A·B·C·D 를 **다** 걸었다.
    #    첫 실행의 판정 문장이 A 만 보고 있었던 것은 **기준이 아니라 출력의
    #    구현 오류**라 고쳤다 — 바를 움직인 것이 아니다 (RESULTS 「정정」 절).
    if a_ok and b_ok and c_ok:
        print("판정: **(나)의 전제가 이 표본에서는 선다.** 다만 구현이 아니라")
        print("   가능성이고, 🔴 **정작 문제가 큰 투구·인사이드 패스의 키포인트가**")
        print("   **없다** — 거기서 다시 봐야 한다.")
    elif a_ok:
        print("판정: 🔴 **(나)의 전제가 이 표본에서 서지 않는다.** 커버리지는")
        print(f"   {best_cov:.0%} 로 넉넉한데(A ✅) **두 큐가 서로 안 맞는다**")
        print(f"   (B {em:.0%} — 우연이 50%다) 그리고 **시간 안정도 못 넘었다**(C).")
        print("   커버리지가 높다는 것은 **값이 나온다**는 뜻이지 **맞다**는")
        print("   뜻이 아니다. 지금 근거로는 어느 큐도 방향을 짚는다고 말할 수")
        print("   없다. 🔴 **실패가 아니라 결론이다.**")
    else:
        print("판정: 🔴 **(나)의 전제가 이 표본에서 서지 않는다.** 커버리지가")
        print(f"   {best_cov:.0%} 로 바(70%)에 못 미친다. 부호를 못 정하는 클립이")
        print("   대부분이면 방향 인식 지표는 그 클립들에서 **값을 못 낸다.**")
        print("   🔴 이것은 실패가 아니라 결론이다 — 그러면 (가)로 가되")
        print("   **앞뒤 구분을 포기하는 대가**를 명시해 적는다.")
    print("🔴 이 회차는 처방을 고르지 않았고 `features.py` 를 고치지 않았다.")
    print("⚠️ 표본이 **전부 야구 타격 39클립**이다. 큐 2 는 제자리 동작이라")
    print("   구조적으로 불리하다 — 여기서 약해도 투구에서 안 된다는 뜻이 아니다.")


if __name__ == "__main__":
    main()
