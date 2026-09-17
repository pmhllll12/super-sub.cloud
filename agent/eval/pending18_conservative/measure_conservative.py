#!/usr/bin/env python3
"""보수적 갱신 — 의심스럽지 않을 때만 참조 외양을 따라간다 (미결 18번 3회차).

    uv run python eval/pending18_conservative/measure_conservative.py  # GPU 불필요

2회차(`eval/pending18_reacquire/`)가 찾은 병목:

  갱신하면    → 갈아탄 뒤의 외양을 배워 잘못된 대상에 고착 (1회차가 이래서 껐다)
  갱신 안 하면 → 옳은 트랙도 닻에서 멀어져 K 를 41까지 올려야 안 깨진다

**이번에 시험하는 것은 그 가운데다.** `app >= UPDATE_TAU` 일 때만 참조를
조금씩 옮기고, 어긋나기 시작하면 멈춘다.

🔴 **채점은 갱신되는 `ref` 가 아니라 항상 `닻` 으로 한다.** 갱신되는 기준으로
채점하면 기준이 답을 따라가 어떤 트랙이든 좋아 보인다 — 채점자와 피채점자를
분리하는 자리다 (`PREREGISTRATION.md`, 커밋 `ab5c733`).

🔴 **`src/` 를 고치지 않는다.** production 은 import 만 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_appearance"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_reacquire"))

from measure_appearance import BOXES, SWITCHING, boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_reacquire import CLIPS, anchor_of, prepared, wrong_and_cover  # noqa: E402
from supersub_agent.pose import _iou, select_subject_boxes  # noqa: E402

# --- 사전 등록 상수 (1·2회차에서 그대로 들고 온 것 + 새 둘) -----------------
TAU = 0.6
REACQ_TAU = 0.6
REACQ_K = 2
UPDATE_TAU = 0.6   # = TAU. 「의심스럽지 않을 때」의 뜻을 새로 만들지 않는다
ALPHA = 0.05       # 표류는 느리다 — 20프레임 규모로 움직이게 둔다

CALIBRATION = sorted(set(BOXES) - SWITCHING)
TEST = sorted(SWITCHING)


def track(auto, cands, frames, subject, fps, wh, K):
    """거부·재획득(2회차) + **보수적 갱신**(이번). 반환 (chosen, 재획득 횟수)."""
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, 0

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = seed
    reacquired = 0

    def app(ref, t, box):
        if ref is None or box is None or t >= len(frames):
            return 1.0
        return similarity(ref, hist_of(frames[t], box))

    def walk(order, start):
        nonlocal reacquired
        # 🔴 방향마다 참조를 닻에서 새로 시작한다. 앞으로 간 뒤의 참조를
        #    뒤로 가는 데 물려주면 시간이 거꾸로 흐른다.
        previous, ref, lost, bad, good = start, ah, False, 0, 0
        for t in order:
            if not lost:
                pick, pick_iou = None, 0.0
                for cand in cands[t]:
                    iou = _iou(previous, cand)
                    if iou > pick_iou:
                        pick, pick_iou = cand, iou
                if pick is None:
                    # 겹치는 후보 0개 — production 과 같게 자동으로 떨어진다.
                    chosen[t] = auto[t]
                    if auto[t] is not None:
                        previous = auto[t]
                    continue
                a = app(ref, t, pick)
                if a < TAU:
                    bad += 1
                    if bad >= K:
                        lost, bad, good = True, 0, 0
                        chosen[t] = None
                        continue
                else:
                    bad = 0
                    # --- 보수적 갱신: 의심스럽지 않을 때만 조금 옮긴다 -----
                    if a >= UPDATE_TAU and t < len(frames):
                        h = hist_of(frames[t], pick)
                        if h is not None and ref is not None:
                            ref = (1.0 - ALPHA) * ref + ALPHA * h
                chosen[t] = pick
                previous = pick
                continue

            # --- 잃은 상태: 외양으로 다시 찾는다 ---------------------------
            # 🔴 재획득은 **닻**으로 판단한다. 잃기 직전의 ref 는 이미 오염
            #    쪽으로 기울었을 수 있어, 그것으로 찾으면 틀린 사람에게 다시
            #    붙는다.
            best, best_app = None, REACQ_TAU
            for cand in cands[t]:
                v = app(ah, t, cand)
                if v >= best_app:
                    best, best_app = cand, v
            if best is None:
                chosen[t] = None
                good = 0
                continue
            good += 1
            if good >= REACQ_K:
                lost, bad, ref = False, 0, ah   # 참조도 닻으로 되돌린다
                reacquired += 1
                chosen[t] = best
                previous = best
            else:
                chosen[t] = None

    walk(range(anchor + 1, n), seed)
    walk(range(anchor - 1, -1, -1), seed)
    return chosen, reacquired


def calibrate() -> int:
    """K = 보정용 7건에서 「app < TAU 가 연속으로 이어진 최대 길이」 + 1.

    2회차와 **같은 규칙**이다. 다른 것은 app 을 재는 참조가 보수적으로
    갱신된다는 것뿐이라, 값의 차이가 곧 갱신의 효과다.
    """
    worst, where = 0, ""
    for clip in CALIBRATION:
        auto, cands, frames, subject, fps, wh, base, _sel = prepared(clip)
        anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        if anchor is None:
            continue
        ref, run = ah, 0
        for t, b in enumerate(base):
            if b is None or t >= len(frames):
                run = 0
                continue
            h = hist_of(frames[t], b)
            a = similarity(ref, h)
            if a < TAU:
                run += 1
                if run > worst:
                    worst, where = run, f"{clip} f{t - run + 1}~f{t}"
            else:
                run = 0
                if a >= UPDATE_TAU and h is not None and ref is not None:
                    ref = (1.0 - ALPHA) * ref + ALPHA * h
    print(f"보정 (깨끗한 {len(CALIBRATION)}건에서만) — app < {TAU} 연속 최대 "
          f"{worst}프레임 ({where or '없음'})")
    return worst + 1


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    K = calibrate()
    print(f"→ **K = {K}**   (2회차는 41이었다 — 사전 예측: 뚜렷하게 작아질 것)")
    print("   " + ("✅ 예측대로 줄었다" if K < 41 else
                   "🔴 예측이 빗나갔다 — 갱신이 표류를 못 잡았다") + "\n")

    print("═" * 92)
    print("시험용 — 갈아탄 3건   (🔴 채점 기준 app 은 **닻**이다, 갱신된 ref 가 아니다)")
    print("═" * 92)
    print(f"  {'clip':14s} {'엉뚱(현)':>8s} {'엉뚱(3회차)':>11s} {'감소':>6s} │ "
          f"{'커버(현)':>8s} {'커버(3회차)':>11s} {'유지':>6s} │ 재획득")
    c_hits, d_fail = 0, []
    for clip in TEST:
        auto, cands, frames, subject, fps, wh, base, _sel = prepared(clip)
        _a, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        new, reacq = track(auto, cands, frames, subject, fps, wh, K)
        w0, c0 = wrong_and_cover(base, frames, ah)
        w1, c1 = wrong_and_cover(new, frames, ah)
        drop = 1.0 - (w1 / w0) if w0 else 0.0
        keep = (c1 / c0) if c0 else 0.0
        if w0 and drop >= 0.70:
            c_hits += 1
        if keep < 0.50:
            d_fail.append(clip)
        print(f"  {clip:14s} {w0:8d} {w1:11d} {drop:5.0%} │ "
              f"{c0:8d} {c1:11d} {keep:5.0%} │ {reacq}")

    print("\n" + "═" * 92)
    print("보정용 — 깨끗한 7건")
    print("═" * 92)
    b_changed = []
    for clip in CALIBRATION:
        auto, cands, frames, subject, fps, wh, base, _sel = prepared(clip)
        new, _re = track(auto, cands, frames, subject, fps, wh, K)
        if list(new) != list(base):
            b_changed.append(f"{clip}({sum(1 for a, b in zip(new, base) if a != b)}프레임)")
    print("  " + ("✅ 7/7 기준선과 동일" if not b_changed
                  else "🔴 바뀐 것: " + ", ".join(b_changed)))

    a_ok = True
    for clip in sorted(BOXES):
        auto, cands, wh, fps = boxes_from_cache(clip)
        got, sel = select_subject_boxes(auto, cands, None, fps, wh)
        if got is not auto or sel.source != "auto":
            a_ok = False
    b_ok, c_ok, d_ok = not b_changed, c_hits >= 2, not d_fail

    print("\n" + "═" * 92)
    print("사전 등록 합격 기준 (2회차와 같게 두었다 — 비교 가능하게)")
    print("═" * 92)
    print(f"  A 자동 경로 비트 동일 ……………… {'✅ 만족' if a_ok else '🔴 불만족'}")
    print(f"  B 보정용 7건 기준선과 동일 …… {'✅ 만족' if b_ok else '🔴 불만족'}")
    print(f"  C 엉뚱 프레임 70%+ 감소 2건+ … {'✅ 만족' if c_ok else '🔴 불만족'}   ({c_hits}/3)")
    print(f"  D 커버리지 50%+ 유지 ……………… {'✅ 만족' if d_ok else '🔴 불만족'}"
          + (f"   (미달: {', '.join(d_fail)})" if d_fail else ""))

    print("\n" + "═" * 92)
    if a_ok and b_ok and c_ok and d_ok:
        print("판정: **합격** — 구현 회차를 열 근거가 생겼다.")
    else:
        print("판정: **불합격.**")
    print("🔴 같은 시험 표본을 **세 번째** 쟀다. 여러 번 시험하면 우연히 통과할")
    print("   확률이 올라간다 — 합격이어도 「고쳤다」가 아니고, 구현 회차에는")
    print("   **이 3건에 없던 클립**이 있어야 한다 (사전 등록).")
    print("🔴 이 회차도 `src/` 를 고치지 않는다.")


if __name__ == "__main__":
    main()
