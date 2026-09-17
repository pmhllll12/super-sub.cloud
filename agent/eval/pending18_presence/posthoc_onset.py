#!/usr/bin/env python3
"""🔴 **사후 관찰** — 사전 등록의 `cont_iou` 가 구간 길이에 오염됐는가.

    uv run python eval/pending18_presence/posthoc_onset.py    # GPU 불필요

🔴 **이것은 판정이 아니다.** 사전 등록(`60d2673`)의 결론은
`measure_presence.out` 에 있는 그대로이고 **여기 숫자로 바꾸지 않는다.**
여기서 하는 일은 **그 결론을 얼마나 믿을 수 있는지**를 재는 것이다.

## 왜 의심하는가

사전 등록의 `drifted_away` 는 `cont_iou < RESCUE_IOU` 다. `cont_iou` 는
**잃은 구간 내내 고정된** `previous`(마지막 좋은 박스)와의 IoU 를 프레임마다
재서 **중앙값**을 취한다.

> **구간이 길면 대상이 있어도 IoU 가 떨어진다.** 사람은 움직이고 `previous`
> 는 안 움직인다. 구간 길이 중앙이 38프레임이라 **길이가 분류를 정했을 수
> 있다** — 그러면 77%는 「대상이 없다」가 아니라 「구간이 길다」를 잰 것이다.

## 길이에 안 휘둘리는 물음

**구간이 시작된 직후** 한두 프레임만 본다. 대상이 있으면 그때는 아직
`previous` 근처에 있어야 하고, 가려졌거나 나갔으면 **그 순간부터** 없다.

`onset_iou(k)` = 구간의 **첫 k 프레임**에서의 `cont_iou` 최대값.
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("src", "eval/phaseA", "eval/pending18_appearance",
            "eval/pending18_reacquire", "eval/pending18_conservative",
            "eval/pending18_scale", "eval/pending18_rescue",
            "eval/pending18_gate", "eval/pending18_coverage",
            "eval/pending18_presence"):
    sys.path.insert(0, str(ROOT / sub))

from measure_appearance import boxes_from_cache  # noqa: E402
from measure_conservative import TAU, calibrate  # noqa: E402
from measure_coverage import TARGET7, build_samples  # noqa: E402
from measure_presence import app_of, lost_runs, track_traced  # noqa: E402
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import RESCUE_IOU, low_from_cache  # noqa: E402
from supersub_agent.pose import SubjectRequest, _iou, read_frames  # noqa: E402

ONSET_K = (1, 2, 3, 5)


def main() -> None:
    main_s, held_s = build_samples()
    by_clip = {c: (b, a) for c, b, a, _ in main_s + held_s}
    K = calibrate()
    print("🔴 사후 관찰이다 — 사전 등록의 결론을 **바꾸지 않는다.** "
          "얼마나 믿을 수 있는지를 잰다.\n")

    rows = []
    for clip in TARGET7:
        if clip not in by_clip:
            continue
        box, at_ms = by_clip[clip]
        auto, cands, wh, fps = boxes_from_cache(clip)
        lows, _f = low_from_cache(clip)
        frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)
        anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        if anchor is None:
            continue
        chosen, state, prev_box = track_traced(auto, cands, lows, frames,
                                               subject, fps, wh, K)
        for s, e in lost_runs(state):
            prev = prev_box[s] if s > anchor else prev_box[e]
            fwd = s > anchor
            order = range(s, e + 1) if fwd else range(e, s - 1, -1)
            per = []
            for t in order:
                pool = list(cands[t]) + [(x, y, bw, bh)
                                         for x, y, bw, bh, _sc in lows[t]]
                iou = max((_iou(prev, c) for c in pool), default=0.0) if prev else 0.0
                a = max((app_of(ah, t, c, frames) for c in pool), default=0.0)
                per.append((iou, a))
            rows.append({
                "clip": clip, "len": e - s + 1,
                "med_iou": st.median([v for v, _ in per]),
                "onset": {k: max((v for v, _ in per[:k]), default=0.0)
                          for k in ONSET_K},
                "onset_app": max((a for _, a in per[:3]), default=0.0),
            })

    print("═" * 96)
    print("구간별 — 중앙 IoU(사전 등록이 쓴 값) 대 **시작 직후** IoU")
    print("═" * 96)
    print(f"  {'clip':16s} {'길이':>5s} │ {'중앙IoU':>7s} │ "
          + " ".join(f"{'onset' + str(k):>8s}" for k in ONSET_K)
          + f" │ {'onset app':>9s}")
    for r in sorted(rows, key=lambda x: -x["len"]):
        mark = "🔴" if r["med_iou"] < RESCUE_IOU <= r["onset"][3] else "  "
        print(f"  {r['clip']:16s} {r['len']:5d} │ {r['med_iou']:7.2f} │ "
              + " ".join(f"{r['onset'][k]:8.2f}" for k in ONSET_K)
              + f" │ {r['onset_app']:9.2f} {mark}")

    print("\n" + "═" * 96)
    print("🔴 길이가 분류를 정했는가")
    print("═" * 96)
    n = len(rows)
    med_out = [r for r in rows if r["med_iou"] < RESCUE_IOU]
    flip = [r for r in med_out if r["onset"][3] >= RESCUE_IOU]
    print(f"  중앙 IoU 로 `drifted_away` 가 된 구간 …………… {len(med_out)}/{n}")
    print(f"  그중 **시작 3프레임**에는 이어지는 후보가 있던 것 … {len(flip)}"
          f" ({len(flip) / len(med_out):.0%})" if med_out else "")
    if flip:
        print("  🔴 이만큼은 「없다」가 아니라 **「멀어졌다」**를 잰 것이다 —")
        print("     `previous` 는 고정인데 사람은 움직인다.")
    lost_all = sum(r["len"] for r in rows)
    flip_frames = sum(r["len"] for r in flip)
    print(f"  프레임 가중으로는 {flip_frames}/{lost_all} = "
          f"{flip_frames / lost_all:.0%} 가 뒤집힌다")

    print("\n  길이와 중앙 IoU 의 관계 (짧은 구간이 정말 IoU 가 높은가)")
    short = [r["med_iou"] for r in rows if r["len"] <= 10]
    long_ = [r["med_iou"] for r in rows if r["len"] > 40]
    if short:
        print(f"    ≤10프레임 구간 {len(short)}개 — 중앙 IoU {st.median(short):.2f}")
    if long_:
        print(f"    >40프레임 구간 {len(long_)}개 — 중앙 IoU {st.median(long_):.2f}")

    print("\n" + "═" * 96)
    print("🔴 시작 IoU 로 다시 나누면 — **사후이고 판정이 아니다**")
    print("═" * 96)
    present = [r for r in rows if r["onset"][3] >= RESCUE_IOU]
    gone = [r for r in rows if r["onset"][3] < RESCUE_IOU]
    pf = sum(r["len"] for r in present)
    gf = sum(r["len"] for r in gone)
    print(f"  시작부터 이어지는 후보가 **없다** (진짜 (가) 후보) … "
          f"{len(gone):2d}구간 {gf:5d}프레임 = {gf / lost_all:.0%}")
    print(f"  시작에는 **있었다** ……………………………………… "
          f"{len(present):2d}구간 {pf:5d}프레임 = {pf / lost_all:.0%}")
    print(f"  🔴 사전 등록이 낸 (가) 77% 와 **거의 뒤집힌다.**")
    print(f"     해당 클립: 없음 = "
          + ", ".join(sorted({r['clip'] for r in gone})))

    print("\n" + "═" * 96)
    print("🔴 대조군 관문이 헛돈 클립이 있는가 (깨끗 프레임이 너무 적으면 공허하다)")
    print("═" * 96)
    for clip in TARGET7:
        if clip not in by_clip:
            continue
        box, at_ms = by_clip[clip]
        auto, cands, wh, fps = boxes_from_cache(clip)
        lows, _f = low_from_cache(clip)
        frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)
        anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        chosen, state, _pb = track_traced(auto, cands, lows, frames,
                                          subject, fps, wh, K)
        clean = [t for t, v in enumerate(state) if v in ("pick", "reacq", "anchor")]
        non_anchor = [t for t in clean if t != anchor]
        vals = [app_of(ah, t, chosen[t], frames) for t in non_anchor]
        note = ("🔴 **닻 한 장뿐** — 자기 자신과의 비교라 관문이 공허하다"
                if not non_anchor else
                f"닻 뺀 {len(non_anchor)}장 중앙 {st.median(vals):.2f}"
                + ("" if st.median(vals) >= TAU else f" 🔴 < {TAU}"))
        print(f"  {clip:16s} 깨끗 {len(clean):4d}장 → {note}")


if __name__ == "__main__":
    main()
