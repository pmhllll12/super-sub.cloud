"""다인 화면에서 고른 사람이 공을 다루는 사람인가 — 미결 `ho` 18번 12회차.

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `2a9373c`)을 먼저 읽는다.** 상수·
합격선·판별 규칙·예측은 이 파일을 쓰기 **전에** 굳었고 결과를 보고 고치지 않는다.

🔴 **11회차 스크립트를 고치지 않고 `import` 한다.** 복제하면 두 회차의 계기가
조용히 갈라진다(미결 10번의 형태). 바뀌는 것은 **표본 하나**뿐이다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. ViTPose 는 안 돌린다.

    cd agent && uv run python eval/pending18_broadcast/measure_broadcast.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_ball_proximity"))

# 🔴 11회차의 계기를 **그대로** 부른다.
from measure_proximity import (  # noqa: E402
    MIN_BALL_COVERAGE,
    MIN_MARGIN,
    MIN_NEAR_FRAMES,
    NEAR,
    NEAR_SWEEP,
    analyse,
    detect_clip,
    foot_point,
    layer,
)
from supersub_agent.pose import _load_detector, PERSON_ELIGIBLE_THRESHOLD  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent

# 🔴 사전 등록에서 **새로 고른 둘**. 결과를 보고 돌리지 않는다.
JITTER_PX = 1.0
JITTER_FLIP_MAX = 0.20
HEIGHT_RATIO_MIN = 2.0   # 기준 G — 11회차의 1.2 에서 올렸다 (사전 등록 5절)


def jitter_flip_rate(det: dict, H: float, rows: list[dict]) -> tuple[float, int]:
    """주 층 프레임에서 박스를 ±1px 흔들면 `argmin` 이 바뀌는 비율.

    🔴 **계기 검사다.** 사람이 28px 인데 거리를 `H` 로 나누므로 1px 는
    0.036 키높이다 — `NEAR`(0.25)의 1/7. 잡음이 순위를 정하고 있으면
    `M` 은 아무 뜻이 없다.

    네 방향(±x, ±y)으로 **모든 후보를 동시에** 흔들지 않고 **한 후보씩**
    흔든다 — 전부 같이 움직이면 상대 순위가 안 바뀌어 검사가 공허해진다.
    """
    cands, chosen = det["cands"], det["chosen"]
    flips = 0
    for r in rows:
        t = r["t"]
        boxes = cands[t]
        ball = r["_ball"]
        base = [np.hypot(*(np.asarray(foot_point(b)) - ball)) / H for b in boxes]
        ai = int(np.argmin(base))
        flipped = False
        for i in range(len(boxes)):
            for dx, dy in ((JITTER_PX, 0), (-JITTER_PX, 0),
                           (0, JITTER_PX), (0, -JITTER_PX)):
                x, y, w, h = boxes[i]
                fx, fy = foot_point((x + dx, y + dy, w, h))
                d = list(base)
                d[i] = float(np.hypot(fx - ball[0], fy - ball[1]) / H)
                if int(np.argmin(d)) != ai:
                    flipped = True
                    break
            if flipped:
                break
        flips += flipped
    return (flips / len(rows) if rows else float("nan")), flips


def main() -> None:
    import torch

    clips = sorted(paths.soccernet_clips_root().glob("*.mp4"))
    if not clips:
        print(f"🔴 클립이 없다: {paths.soccernet_clips_root()}\n"
              "   eval/sample_gate/fetch_soccernet.py 로 먼저 받는다 "
              "(hf auth login 필요).")
        raise SystemExit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"SoccerNet 방송 {len(clips)}편 · device={device} · NEAR={NEAR} "
          f"eligible≥{PERSON_ELIGIBLE_THRESHOLD} · JITTER={JITTER_PX}px\n")
    print("🔴 이 표본은 **방송**이다. 선택 규칙이 어떻게 깨지는가를 재는 것이지")
    print("   제품에서 몇 %가 깨지는가가 아니다 (사전 등록 1절).\n")

    det_pair = _load_detector(device)
    out_rows, jitter_num, jitter_den = [], 0, 0

    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            det = detect_clip(clip, det_pair, device)
            res = analyse(det)
        except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 회차는 돈다
            print(f"  [{i}/{len(clips)}] {clip.name[:38]:38s} ⚠️ {type(exc).__name__}")
            out_rows.append({"clip": clip.name, "error": repr(exc)})
            continue
        if res is None or "rows" not in res:
            out_rows.append({"clip": clip.name,
                             "skipped": (res or {}).get("skipped", "후보 없음")})
            print(f"  [{i}/{len(clips)}] {clip.name[:38]:38s} 건너뜀")
            continue

        # 주 층과 섭동 검사는 같은 프레임 집합에서 돈다.
        main_layer = layer(res["rows"], NEAR)
        # 섭동에 필요한 공 좌표를 프레임 행에 붙인다 (11회차 계기는 거리만 남긴다).
        ball_raw = det["objects"].get("sports_ball")
        H = res["scale_h"]
        for r in main_layer:
            r["_ball"] = ball_raw[r["t"], :2]
        rate, flips = jitter_flip_rate(det, H, main_layer)
        for r in main_layer:
            del r["_ball"]
        if main_layer:
            jitter_num += flips
            jitter_den += len(main_layer)

        m = (sum(r["match"] for r in main_layer) / len(main_layer)
             if main_layer else None)
        res.update({"clip": clip.name, "seconds": round(time.time() - t0, 1),
                    "n_near": len(main_layer),
                    "m_clip": round(m, 3) if m is not None else None,
                    "jitter_flip": round(rate, 3) if main_layer else None})
        out_rows.append(res)
        print(f"  [{i}/{len(clips)}] {clip.name[:38]:38s} "
              f"공커버 {res['ball_coverage']:.0%} · 주층 {len(main_layer):3d}f · "
              f"일치 {'—' if m is None else f'{m:3.0%}'} · "
              f"섭동 {'—' if not main_layer else f'{rate:3.0%}'}  "
              f"({res['seconds']}초)")

    (HERE / "broadcast_raw.json").write_text(
        json.dumps(out_rows, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [r for r in out_rows
          if "error" not in r and "skipped" not in r
          and r.get("ball_coverage", 0) >= MIN_BALL_COVERAGE
          and r.get("n_near", 0) >= MIN_NEAR_FRAMES]
    dropped = [r for r in out_rows if r not in ok]

    print("\n" + "=" * 72)
    print(f"분모 {len(ok)}/{len(clips)} 편 "
          f"(공 커버 <{MIN_BALL_COVERAGE:.0%} · 주 층 <{MIN_NEAR_FRAMES}프레임 등으로 "
          f"뺀 것 {len(dropped)}편)")
    if not ok:
        print("🔴 분모가 비었다 — 판정할 수 없다")
        return

    all_rows = [r for c in ok for r in c["rows"]]
    main_layer = layer(all_rows, NEAR)
    matched = [r for r in main_layer if r["match"]]
    miss = [r for r in main_layer if not r["match"]]
    M = len(matched) / len(main_layer)
    m_clip = [c["m_clip"] for c in ok if c["m_clip"] is not None]
    margins = sorted(r["d_chosen"] - r["d_min"] for r in miss)
    margin_med = statistics.median(margins) if margins else float("nan")
    ratios = sorted(r["h_chosen"] / r["h_argmin"] for r in miss if r["h_argmin"] > 0)
    ratio_med = statistics.median(ratios) if ratios else float("nan")
    total_frames = sum(c["frames"] for c in ok)
    single = [r for r in all_rows if r["d_min"] <= NEAR and r["n_cands"] < 2]
    flip_rate = jitter_num / jitter_den if jitter_den else float("nan")

    print(f"\n주 지표 M (프레임 가중) : {M:.1%}  ({len(matched)}/{len(main_layer)})")
    print(f"          클립 가중      : 중앙 {statistics.median(m_clip):.1%} · "
          f"분포 {[f'{v:.0%}' for v in sorted(m_clip)]}")
    if margins:
        print(f"불일치 margin (키높이)  : 중앙 {margin_med:.3f} · "
              f"범위 {margins[0]:.3f}~{margins[-1]:.3f}")

    b_ok = flip_rate < JITTER_FLIP_MAX
    print("\n── 사전 등록 판정 A~G")
    print(f"  A 주 층에 단일후보 0건        : {len(single)}건 "
          f"{'✅' if not single else '🔴'}")
    print(f"  B 🔴 계기 — ±{JITTER_PX:.0f}px 섭동 flip <{JITTER_FLIP_MAX:.0%} "
          f": {flip_rate:.1%} ({jitter_num}/{jitter_den}) {'✅' if b_ok else '🔴'}")
    print("  C src/·rubrics/ 무변경        : ✅ (11회차를 import 만 한다)")
    print(f"  D reach                       : 주 층 {len(main_layer)}/{total_frames} "
          f"프레임 ({len(main_layer)/total_frames:.1%}) · 클립 {len(ok)}/{len(clips)}")

    print("  E 민감도 (NEAR 네 값)")
    verdicts = []
    for near in NEAR_SWEEP:
        lay = layer(all_rows, near)
        if not lay:
            print(f"      NEAR={near:.2f} : 주 층 비어 있음")
            verdicts.append("빈층")
            continue
        mm = sum(r["match"] for r in lay) / len(lay)
        mg = [r["d_chosen"] - r["d_min"] for r in lay if not r["match"]]
        mgm = statistics.median(mg) if mg else float("nan")
        v = ("가" if mm >= 0.70 else
             "나" if (mm <= 0.30 and mgm >= MIN_MARGIN) else "불가")
        verdicts.append(v)
        print(f"      NEAR={near:.2f} : 주층 {len(lay):4d}f · M {mm:5.1%} · "
              f"margin 중앙 {mgm:.3f} → ({v})")
    print(f"      → 판정 구간 불변 : "
          f"{'✅' if len(set(verdicts)) == 1 else '🔴 문턱에 업혀 있다'}")

    print("  F pytest                      : 별도로 돌린다")
    if M < 0.50:
        print(f"  G 짝 기준 (M<50% 이므로 적용) : 불일치 프레임 높이비 중앙 "
              f"{ratio_med:.2f} ≥ {HEIGHT_RATIO_MIN} "
              f"{'✅ 원근 기전 확인' if ratio_med >= HEIGHT_RATIO_MIN else '🔴 기전 미설명 → 판별불가로 내린다'}")
    else:
        print(f"  G 짝 기준                     : 해당 없음 (M={M:.1%} ≥ 50%)")

    # ── 판별 규칙 (사전 등록 4절) ─────────────────────────────────────
    print()
    if not b_ok:
        verdict = ("🔴 판별불가 — **기준 B 불통과**. 섭동이 순위를 바꾸므로 "
                   "M 을 판정에 쓰지 않는다")
    elif M >= 0.70:
        verdict = "(가) 선택은 맞다 — 다인 화면에서도 공 가진 사람을 고른다"
    elif M <= 0.30 and margin_med >= MIN_MARGIN and ratio_med >= HEIGHT_RATIO_MIN:
        verdict = "(나) 선택이 틀린다 — 원근 기전까지 확인됐다"
    elif M <= 0.30 and margin_med >= MIN_MARGIN:
        verdict = (f"판별불가 — M·margin 은 (나)인데 높이비 {ratio_med:.2f} < "
                   f"{HEIGHT_RATIO_MIN} 라 기전이 설명 안 된다 (G)")
    elif M <= 0.30:
        verdict = (f"판별불가 — M 은 낮은데 margin 중앙 {margin_med:.3f} < "
                   f"{MIN_MARGIN} (계기 해상도)")
    else:
        verdict = "판별불가 — 30~70% 사이"
    print(f"🔴 판정: {verdict}")
    print(f"\n🔴 내 사전 예측은 **(나)** 였다. 위와 다르면 **틀렸다고 적는다.**")

    # ── 사후 관찰 (판정에 안 쓴다) ────────────────────────────────────
    print("\n── 사후 관찰 (판정에 안 쓴다)")
    near_all = [r for r in all_rows if r["d_min"] <= NEAR]
    if near_all:
        print(f"  공이 발치에 온 프레임 {len(near_all)} 중 단일후보 "
              f"{len(single)} ({len(single)/len(near_all):.0%})")
    print(f"  주 층 후보 수: 중앙 "
          f"{statistics.median([r['n_cands'] for r in main_layer])} · "
          f"최대 {max(r['n_cands'] for r in main_layer)}")
    hs = [r["h_chosen"] for r in main_layer]
    print(f"  고른 사람 박스 높이: 중앙 {statistics.median(hs):.0f}px "
          f"· 범위 {min(hs):.0f}~{max(hs):.0f}")
    if ratios:
        print(f"  불일치 높이비 분포: p25 {ratios[len(ratios)//4]:.2f} · "
              f"중앙 {ratio_med:.2f} · p75 {ratios[3*len(ratios)//4]:.2f}")


if __name__ == "__main__":
    main()
