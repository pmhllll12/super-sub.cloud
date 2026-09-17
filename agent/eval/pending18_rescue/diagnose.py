#!/usr/bin/env python3
"""왜 D 가 빗나갔는가 — 진단만 한다 (미결 18번 5회차 부록).

    uv run python eval/pending18_rescue/diagnose.py    # GPU 불필요

`measure_rescue.py` 가 낸 결과 두 가지가 설명을 요구한다.

  (1) 커버가 무너진 넷 중 **셋은 구제가 0~1회**밖에 안 걸렸다 — 그 클립의
      커버리지 손실은 「대상이 버려졌다」로 설명되지 않는다는 뜻이다
  (2) 4회차의 표제 사례 `sGKeqfxwq5E` f169 를 구제했는데 **클립은 나아지지
      않았다**(감소 54% → 53%)

🔴 **여기서 처방을 바꾸지 않는다.** 새 처방은 새 사전 등록을 받는다.
이 파일은 「무엇이 프레임을 잃게 했는가」를 세기만 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("src", "eval/phaseA", "eval/pending18_appearance",
            "eval/pending18_reacquire", "eval/pending18_conservative",
            "eval/pending18_scale", "eval/pending18_rescue"):
    sys.path.insert(0, str(ROOT / sub))

from measure_appearance import BOXES, boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_conservative import REACQ_TAU, TAU, calibrate  # noqa: E402
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import D_CLIPS, RESCUE_IOU, build_sample, low_from_cache, track_rescue  # noqa: E402
from supersub_agent.pose import SubjectRequest, _iou, read_frames, select_subject_boxes  # noqa: E402


def why_lost(auto, cands, lows, frames, subject, fps, wh, K):
    """잃은 프레임을 사유별로 센다 — 구제가 닿을 수 있는 자리인가.

    `track_rescue` 의 걷기를 **똑같이** 다시 걷되 아무것도 바꾸지 않고
    세기만 한다. 반환은 세 수:

      lost_frames  — 잃은 상태로 흘려보낸 프레임 수
      reachable    — 그중 **직전 박스와 IoU ≥ 0.3 인 임계 미달 검출이 있는** 것
                     (= 구제를 재획득까지 열면 닿을 수 있었을 자리)
      pass_ok      — 그중 **통과 후보**가 이미 IoU ≥ 0.3 으로 겹쳐 있던 것
                     (= 대상은 후보에 있었고 외양 검사가 거부한 것)
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return 0, 0, 0
    chosen, _rq, _ev = track_rescue(auto, cands, lows, frames, subject, fps, wh, K)

    lost_frames = reachable = pass_ok = 0
    for order in (range(anchor + 1, n), range(anchor - 1, -1, -1)):
        last = seed
        for t in order:
            if chosen[t] is not None:
                last = chosen[t]
                continue
            lost_frames += 1
            if max((_iou(last, c) for c in cands[t]), default=0.0) >= RESCUE_IOU:
                pass_ok += 1
            if max((_iou(last, (x, y, w, h)) for x, y, w, h, _s in lows[t]),
                   default=0.0) >= RESCUE_IOU:
                reachable += 1
    return lost_frames, reachable, pass_ok


def main() -> None:
    K = calibrate()
    sample = {c: (b, ms) for c, b, ms, _a, _h in build_sample()}
    look = D_CLIPS + ["sGKeqfxwq5E", "X6dC9pu5H3k", "CFjNxCZhn_8"]

    print("\n" + "═" * 96)
    print("(1) 잃은 프레임의 사유 — 구제가 닿을 수 있는 자리였는가")
    print("═" * 96)
    print(f"  {'clip':16s} │ {'잃음':>6s} {'통과후보 있었음':>14s} "
          f"{'미달후보 있었음':>14s}")
    for clip in D_CLIPS:
        box, at_ms = sample[clip]
        auto, cands, wh, fps = boxes_from_cache(clip)
        lows, _f = low_from_cache(clip)
        frames, _s1, _s2 = read_frames(CLIPS / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)
        lost, reach, pok = why_lost(auto, cands, lows, frames, subject, fps, wh, K)
        print(f"  {clip:16s} │ {lost:6d} {pok:14d} {reach:14d}")
    print("\n  🔴 「통과후보 있었음」이 크면 대상은 **버려지지 않았다** — 후보에")
    print("     있는데 외양 검사가 거부한 것이고, 구제로는 닿지 않는 실패다.")
    print("  🔴 「미달후보 있었음」은 **재획득까지 구제를 열면** 닿았을 자리다.")
    print("     이번 사전 등록은 이어가기로 한정했다(한 회차에 한 가지).")

    print("\n" + "═" * 96)
    print("(2) 구제가 걸린 자리 — 무엇을 되찾았고 그 뒤 무슨 일이 있었는가")
    print("═" * 96)
    for clip in look:
        if clip not in sample:
            continue
        box, at_ms = sample[clip]
        auto, cands, wh, fps = boxes_from_cache(clip)
        lows, _f = low_from_cache(clip)
        frames, _s1, _s2 = read_frames(CLIPS / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)
        _a, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        chosen, _rq, ev = track_rescue(auto, cands, lows, frames, subject,
                                       fps, wh, K)
        if not ev:
            print(f"\n  {clip} — 구제 0회")
            continue
        print(f"\n  {clip} — 구제 {len(ev)}회")
        print(f"    {'f':>5s} {'점수':>5s} {'구제IoU':>7s} {'통과IoU':>7s} "
              f"{'app(닻)':>7s}  이후")
        for e in ev[:12]:
            t = e["t"]
            after = [t2 for t2 in range(t + 1, min(t + 6, len(chosen)))]
            tail = "".join("·" if chosen[t2] is not None else "×" for t2 in after)
            print(f"    {t:5d} {e['score']:5.2f} {e['iou_low']:7.2f} "
                  f"{e['iou_pass']:7.2f} {e['app']:7.2f}  {tail}")
        if len(ev) > 12:
            print(f"    … {len(ev) - 12}회 더")
    print("\n  이후: 구제 다음 5프레임이 채워졌으면 `·`, 잃었으면 `×`")

    print("\n" + "═" * 96)
    print("🔴 진단만 했다. 처방을 바꾸지 않았고, 새 처방은 새 사전 등록을 받는다.")


if __name__ == "__main__":
    main()
