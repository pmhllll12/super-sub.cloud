#!/usr/bin/env python3
"""거부·재획득 — 「안 고를 수 있게」 하면 갈아타기가 멎는가 (미결 18번 2회차).

    uv run python eval/pending18_reacquire/measure_reacquire.py   # GPU 불필요

1회차(`eval/pending18_appearance/`)에서 **재가중은 원리적으로 안 된다**가
나왔다 — 갈아타는 프레임에 겹치는 후보가 1개뿐이라 무엇을 곱해도 argmax 가
안 바뀐다. 다만 **외양 신호 자체는 갈렸다.** 쓸 자리가 없었을 뿐이다.

그래서 이번에는 「고르는 방법」이 아니라 **「안 고를 수 있는가」**를 본다.

  거부   — 이어갈 후보의 외양이 닻과 **K프레임 연속** 어긋나면 고르지 않는다
  재획득 — 잃은 뒤에는 IoU 사슬을 버리고 **외양으로** 다시 붙는다

🔴 **문턱은 깨끗한 7건(보정용)에서만 정한다.** 갈아탄 3건(시험용)을 보고
고치면 이 회차는 무효다 — 자유도가 넷인데 시험 표본이 실질 2건이라
맞추면 측정이 아니라 외우기가 된다. 규칙은 `PREREGISTRATION.md`(`807af0a`).

🔴 **`src/` 를 고치지 않는다.** production 은 import 만 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_appearance"))

from measure_appearance import (  # noqa: E402
    BOXES,
    SWITCHING,
    boxes_from_cache,
    hist_of,
    similarity,
)
from supersub_agent.pose import (  # noqa: E402
    MIN_ANCHOR_IOU,
    SubjectRequest,
    _iou,
    anchor_frame_for,
    read_frames,
    select_subject_boxes,
)

CLIPS = Path("/mnt/d/supersub-phaseA/clips")

# --- 사전 등록 상수 ---------------------------------------------------------
TAU = 0.6         # 외양 문턱 (1회차 보고에서 쓴 값 그대로)
REACQ_TAU = 0.6   # 재획득 문턱 — TAU 와 같게 둔다 (자유도를 안 늘린다)
REACQ_K = 2       # 재획득에 필요한 연속 프레임 (가장 작은 「연속」)
# K 는 보정용 7건에서 유도한다 — 아래 calibrate().

CALIBRATION = sorted(set(BOXES) - SWITCHING)   # 깨끗한 7건
TEST = sorted(SWITCHING)                        # 갈아탄 3건


def prepared(clip: str):
    """(auto, candidates, frames, subject, fps, wh, 기준선 선택)."""
    box, at_ms = BOXES[clip]
    auto, cands, wh, fps = boxes_from_cache(clip)
    frames, _src, _s = read_frames(CLIPS / f"{clip}.mp4")
    subject = SubjectRequest(box=box, at_ms=at_ms)
    base, sel = select_subject_boxes(auto, cands, subject, fps, wh)
    return auto, cands, frames, subject, fps, wh, base, sel


def anchor_of(auto, cands, frames, subject, fps, wh):
    n = len(auto)
    W, H = wh
    anchor, _o, _c = anchor_frame_for(subject.at_ms, fps, n)
    x, y, bw, bh = subject.box
    pb = (x * W, y * H, bw * W, bh * H)
    best_iou, best = 0.0, None
    for cand in cands[anchor]:
        iou = _iou(pb, cand)
        if iou > best_iou:
            best_iou, best = iou, cand
    if best is None or best_iou < MIN_ANCHOR_IOU:
        return None, None, None
    return anchor, best, hist_of(frames[anchor], best)


def calibrate() -> int:
    """K = 보정용 7건에서 「app < TAU 가 연속으로 이어진 최대 길이」 + 1.

    🔴 **깨끗한 클립이 하나도 안 끊기는 가장 짧은 길이**다. 시험용은 안 본다.
    """
    worst, where = 0, ""
    for clip in CALIBRATION:
        auto, cands, frames, subject, fps, wh, base, _sel = prepared(clip)
        anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        if anchor is None:
            continue
        run = 0
        for t, b in enumerate(base):
            if b is None or t >= len(frames):
                run = 0
                continue
            if similarity(ah, hist_of(frames[t], b)) < TAU:
                run += 1
                if run > worst:
                    worst, where = run, f"{clip} f{t - run + 1}~f{t}"
            else:
                run = 0
    print(f"보정 (깨끗한 {len(CALIBRATION)}건에서만) — app < {TAU} 연속 최대 "
          f"{worst}프레임 ({where or '없음'})")
    return worst + 1


def track(auto, cands, frames, subject, fps, wh, K):
    """거부·재획득을 넣은 이어가기. 반환 (chosen, 거부 프레임 수, 재획득 횟수)."""
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, 0, 0

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = seed
    rejected = reacquired = 0

    def app_of(t, box):
        if t >= len(frames) or box is None:
            return 1.0        # 못 재면 벌하지 않는다 (1회차와 같은 규약)
        return similarity(ah, hist_of(frames[t], box))

    def walk(order, start):
        nonlocal rejected, reacquired
        previous, lost, bad, good = start, False, 0, 0
        for t in order:
            if not lost:
                pick, pick_iou = None, 0.0
                for cand in cands[t]:
                    iou = _iou(previous, cand)
                    if iou > pick_iou:
                        pick, pick_iou = cand, iou
                if pick is None:
                    # 겹치는 후보 0개 — production 과 **같게** 자동으로 떨어진다.
                    # 이 회차가 바꾸는 것은 「외양 때문에 거부」 하나뿐이다.
                    chosen[t] = auto[t]
                    if auto[t] is not None:
                        previous = auto[t]
                    continue
                if app_of(t, pick) < TAU:
                    bad += 1
                    if bad >= K:
                        # ⚠️ 문턱을 넘긴 프레임부터 거둔다. 앞선 K-1 프레임은
                        # 이미 골라 둔 채로 남는다 — 그 구간도 엉뚱할 수
                        # 있으나, 거슬러 지우는 것은 **자유도를 하나 더** 늘리는
                        # 설계라 이 회차에서 하지 않는다. 남는 오염은 아래
                        # 「엉뚱한 사람 프레임」 수에 그대로 잡힌다.
                        lost, bad, good = True, 0, 0
                        chosen[t] = None
                        rejected += 1
                        continue
                else:
                    bad = 0
                chosen[t] = pick
                previous = pick
                continue

            # --- 잃은 상태: IoU 사슬을 버리고 외양으로 찾는다 ---------------
            best, best_app = None, REACQ_TAU
            for cand in cands[t]:
                a = app_of(t, cand)
                if a >= best_app:
                    best, best_app = cand, a
            if best is None:
                chosen[t] = None
                rejected += 1
                good = 0
                continue
            good += 1
            if good >= REACQ_K:
                lost, bad = False, 0
                reacquired += 1
                chosen[t] = best
                previous = best
            else:
                chosen[t] = None
                rejected += 1

    walk(range(anchor + 1, n), seed)
    walk(range(anchor - 1, -1, -1), seed)
    return chosen, rejected, reacquired


def wrong_and_cover(boxes, frames, ah) -> tuple[int, int]:
    """(엉뚱한 사람 프레임, 대상 커버리지). 엉뚱 = 박스가 있고 app < TAU."""
    wrong = cover = 0
    for t, b in enumerate(boxes):
        if b is None:
            continue
        cover += 1
        if t < len(frames) and similarity(ah, hist_of(frames[t], b)) < TAU:
            wrong += 1
    return wrong, cover


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    K = calibrate()
    print(f"→ **K = {K}** (이 값만 데이터에서 오고, 그 데이터는 보정용뿐이다)\n")

    print("═" * 92)
    print("시험용 — 갈아탄 3건")
    print("═" * 92)
    print(f"  {'clip':14s} {'엉뚱(현)':>8s} {'엉뚱(거부)':>10s} {'감소':>6s} │ "
          f"{'커버(현)':>8s} {'커버(거부)':>10s} {'유지':>6s} │ 재획득")
    c_hits, d_fail = 0, []
    for clip in TEST:
        auto, cands, frames, subject, fps, wh, base, _sel = prepared(clip)
        _a, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        new, _rej, reacq = track(auto, cands, frames, subject, fps, wh, K)
        w0, c0 = wrong_and_cover(base, frames, ah)
        w1, c1 = wrong_and_cover(new, frames, ah)
        drop = 1.0 - (w1 / w0) if w0 else 0.0
        keep = (c1 / c0) if c0 else 0.0
        if w0 and drop >= 0.70:
            c_hits += 1
        if keep < 0.50:
            d_fail.append(clip)
        print(f"  {clip:14s} {w0:8d} {w1:10d} {drop:5.0%} │ "
              f"{c0:8d} {c1:10d} {keep:5.0%} │ {reacq}")

    print("\n" + "═" * 92)
    print("보정용 — 깨끗한 7건 (여기가 바뀌면 K 규칙을 잘못 구현한 것이다)")
    print("═" * 92)
    b_changed = []
    for clip in CALIBRATION:
        auto, cands, frames, subject, fps, wh, base, _sel = prepared(clip)
        new, _rej, _re = track(auto, cands, frames, subject, fps, wh, K)
        if list(new) != list(base):
            diff = sum(1 for a, b in zip(new, base) if a != b)
            b_changed.append(f"{clip}({diff}프레임)")
    print("  " + ("✅ 7/7 기준선과 동일" if not b_changed
                  else "🔴 바뀐 것: " + ", ".join(b_changed)))

    # --- 사전 등록 합격 기준 ------------------------------------------------
    a_ok = True
    for clip in sorted(BOXES):
        auto, cands, wh, fps = boxes_from_cache(clip)
        got, sel = select_subject_boxes(auto, cands, None, fps, wh)
        if got is not auto or sel.source != "auto":
            a_ok = False

    b_ok = not b_changed
    c_ok = c_hits >= 2
    d_ok = not d_fail

    print("\n" + "═" * 92)
    print("사전 등록 합격 기준 (결과를 보고 바꾸지 않는다)")
    print("═" * 92)
    print(f"  A 자동 경로 비트 동일 ……………… {'✅ 만족' if a_ok else '🔴 불만족'}")
    print(f"  B 보정용 7건 기준선과 동일 …… {'✅ 만족' if b_ok else '🔴 불만족'}")
    print(f"  C 엉뚱 프레임 70%+ 감소 2건+ … {'✅ 만족' if c_ok else '🔴 불만족'}"
          f"   ({c_hits}/3)")
    print(f"  D 커버리지 50%+ 유지 ……………… {'✅ 만족' if d_ok else '🔴 불만족'}"
          + (f"   (미달: {', '.join(d_fail)})" if d_fail else ""))

    print("\n" + "═" * 92)
    if a_ok and b_ok and c_ok and d_ok:
        print("판정: **합격** — 구현 회차를 열 근거가 생겼다.")
        print("🔴 「갈아타기를 고쳤다」가 아니다 — 시험 표본이 2~3건이다.")
        print("   이것은 개발 단계이지 검증이 아니다.")
    else:
        print("판정: **불합격.**")
        print("🔴 「외양으로는 안 된다」가 아니다 — 문턱 하나를 재 본 것이다.")
    print("🔴 어느 쪽이든 이 회차는 `src/` 를 고치지 않는다.")


if __name__ == "__main__":
    main()
