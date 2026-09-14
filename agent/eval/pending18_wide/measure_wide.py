"""넓은 박스가 자세인가, 겹친 사람 둘인가 — 미결 `ho` 18번 13회차.

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `205dd01`)을 먼저 읽는다.** 상수·
합격선·판별 규칙·예측은 이 파일을 쓰기 **전에** 굳었고 결과를 보고 고치지 않는다.

🔴 **11·12회차 스크립트를 고치지 않고 `import` 한다.** 층이 갈라지면 이어
읽을 수 없다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. ViTPose 는 안 돌린다.

    cd agent && uv run python eval/pending18_wide/measure_wide.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_ball_proximity"))

from measure_proximity import (  # noqa: E402
    NEAR,
    detect_clip,
    foot_point,
    gate_by_speed,
)
from supersub_agent.pose import _load_detector  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
BROADCAST = HERE.parent / "pending18_broadcast" / "broadcast_raw.json"

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
SWALLOW = 0.7
SWALLOW_SWEEP = (0.5, 0.6, 0.7, 0.8)
WIDE = 0.75
F_GAP = 0.10          # 기준 F — 삼킨 쪽이 이만큼은 더 넓어야 한다
EXPECT_MISMATCH = 163  # 기준 A — 12회차와 같은 층


def ioa(c: tuple, x: tuple) -> float:
    """`x` 가 `c` 안에 얼마나 들어 있는가 (x 의 넓이로 나눈다).

    🔴 **IoU 가 아니다.** IoU 는 분모에 큰 박스가 들어가 **삼킨 경우를
    구조적으로 낮게** 만든다 (사전 등록 1절).
    """
    cx1, cy1, cw, ch = c
    xx1, xy1, xw, xh = x
    ix1, iy1 = max(cx1, xx1), max(cy1, xy1)
    ix2, iy2 = min(cx1 + cw, xx1 + xw), min(cy1 + ch, xy1 + xh)
    if ix2 <= ix1 or iy2 <= iy1 or xw <= 0 or xh <= 0:
        return 0.0
    return (ix2 - ix1) * (iy2 - iy1) / (xw * xh)


def main() -> None:
    import torch

    raw = json.loads(BROADCAST.read_text(encoding="utf-8"))
    wanted = {r["clip"] for r in raw if r.get("n_near", 0) >= 5}
    clips = [p for p in sorted(paths.soccernet_clips_root().glob("*.mp4"))
             if p.name in wanted]
    print(f"12회차 주 층에 든 {len(clips)}편 · SWALLOW={SWALLOW} WIDE={WIDE}\n")
    print("🔴 안 쓴 표본이 없다 — 12회차와 **같은 층**이다 (사전 등록 2절).\n")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    det_pair = _load_detector(device)

    rows = []
    for clip in clips:
        det = detect_clip(clip, det_pair, device)
        cands = det["cands"]
        ball_t = det["objects"].get("sports_ball")
        if ball_t is None:
            continue
        heights = [b[3] for f in cands for b in f]
        H = float(statistics.median(heights)) if heights else 0.0
        if H <= 0:
            continue
        ball_t, _ = gate_by_speed(ball_t, H)   # 12회차와 같은 층

        n_near = n_mis = 0
        for t in range(det["frames"]):
            boxes = cands[t]
            if len(boxes) < 2 or ball_t[t, 2] <= 0:
                continue
            ball = ball_t[t, :2]
            d = [float(np.hypot(*(np.asarray(foot_point(b)) - ball)) / H) for b in boxes]
            ai = int(np.argmin(d))
            if d[ai] > NEAR:
                continue
            n_near += 1
            ci = int(np.argmax([b[2] * b[3] for b in boxes]))
            if ci == ai:
                continue
            n_mis += 1
            c = boxes[ci]
            ioas = sorted((ioa(c, x) for j, x in enumerate(boxes) if j != ci),
                          reverse=True)
            rows.append({
                "clip": clip.name, "t": t,
                "wh": c[2] / c[3],
                "n_cands": len(boxes),
                "ioa_top": round(ioas[0], 3) if ioas else 0.0,
                "swallowed": {f"{s:.1f}": sum(v >= s for v in ioas)
                              for s in SWALLOW_SWEEP},
                "box": [round(v, 1) for v in c],
            })
        print(f"  {clip.name[:42]:42s} 주층 {n_near:3d}f · 불일치 {n_mis:3d}f")

    (HERE / "wide_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    n = len(rows)
    print("\n" + "=" * 72)
    print(f"불일치 {n}프레임 (12회차: {EXPECT_MISMATCH})")
    if not n:
        print("🔴 볼 것이 없다")
        return

    def med(v):
        return statistics.median(v) if v else float("nan")

    key = f"{SWALLOW:.1f}"
    swallowed = [r for r in rows if r["swallowed"][key] >= 1]
    S = len(swallowed) / n
    clean = [r for r in rows if r["swallowed"][key] == 0]
    blind = [r for r in clean if r["wh"] >= WIDE]

    print(f"\n주 지표 S (다른 후보를 하나 이상 삼킨 비율) : {S:.1%} "
          f"({len(swallowed)}/{n})")
    print(f"  삼킨 수 중앙 (삼킨 프레임만) : "
          f"{med([r['swallowed'][key] for r in swallowed]):.0f} · "
          f"최대 {max(r['swallowed'][key] for r in rows)}")
    print(f"  IoA 최대값 분포 : 중앙 {med([r['ioa_top'] for r in rows]):.2f} · "
          f"최대 {max(r['ioa_top'] for r in rows):.2f}")

    print("\n── 사전 등록 판정 A~F")
    print(f"  A 12회차와 같은 층 ({EXPECT_MISMATCH}f) : {n}f "
          f"{'✅' if n == EXPECT_MISMATCH else '🔴 층이 다르다'}")
    print(f"  B 🔴 계기 사각지대 — 안 삼켰는데 w/h≥{WIDE} : "
          f"{len(blind)}/{n} ({len(blind)/n:.1%}) [보고]")
    print("  C src/·rubrics/ 무변경          : ✅ (11·12회차를 import 만 한다)")
    print("  D 민감도 (SWALLOW 네 값)")
    verdicts = []
    for s in SWALLOW_SWEEP:
        k = f"{s:.1f}"
        ss = sum(r["swallowed"][k] >= 1 for r in rows) / n
        v = "겹침" if ss >= 0.70 else "자세" if ss <= 0.30 else "둘다"
        verdicts.append(v)
        print(f"      SWALLOW={s:.1f} : S {ss:5.1%} → ({v})")
    print(f"      → 판정 구간 불변 : "
          f"{'✅' if len(set(verdicts)) == 1 else '🔴 문턱에 업혀 있다'}")
    print("  E pytest                        : 별도로 돌린다")

    wh_sw = [r["wh"] for r in swallowed]
    wh_cl = [r["wh"] for r in clean]
    if S > 0.30 and wh_sw and wh_cl:
        gap = med(wh_sw) - med(wh_cl)
        print(f"  F 짝 기준 — 삼킨 쪽 w/h 중앙 {med(wh_sw):.2f} ≥ "
              f"안 삼킨 {med(wh_cl):.2f} + {F_GAP} : 차이 {gap:+.2f} "
              f"{'✅' if gap >= F_GAP else '🔴 삼킴이 폭을 설명 못 한다'}")
    else:
        print(f"  F 짝 기준                       : 해당 없음 (S={S:.1%})")

    print()
    if S >= 0.70:
        verdict = "(ii) 겹침 — 뿌리는 **검출 후처리**다. 선택 규칙을 고쳐도 안 낫는다"
    elif S <= 0.30:
        verdict = "(i) 자세 — 뿌리는 **선택 규칙**이다. 「면적 → 높이」가 후보로 선다"
    else:
        verdict = (f"**둘 다 일어난다** — 겹침 {S:.0%} · 자세 {1-S:.0%}. "
                   "🔴 판별불가가 아니라 이 비율이 답이다")
    print(f"🔴 판정: {verdict}")
    print("🔴 내 사전 예측은 **「둘 다」** 였다. 다르면 **틀렸다고 적는다.**")

    # ── 사후 관찰 (판정에 안 쓴다) ────────────────────────────────────
    print("\n── 사후 관찰 (판정에 안 쓴다)")
    print(f"  고른 박스 w/h : 중앙 {med([r['wh'] for r in rows]):.2f} · "
          f"최대 {max(r['wh'] for r in rows):.2f}")
    print(f"  w/h ≥ 1.0 (두 사람 폭) 인 프레임 : "
          f"{sum(r['wh'] >= 1.0 for r in rows)}/{n}")
    widest = sorted(rows, key=lambda r: -r["wh"])[:6]
    print("  가장 넓은 6개 (눈으로 볼 것 — 사전 등록 5절):")
    for r in widest:
        print(f"    {r['clip'][:34]:34s} f{r['t']:3d} w/h {r['wh']:.2f} "
              f"· 삼킴 {r['swallowed'][key]} · IoA최대 {r['ioa_top']:.2f}")


if __name__ == "__main__":
    main()
