#!/usr/bin/env python3
"""상류 처방 — 버려진 검출을 이어가기에서만 구제한다 (미결 18번 5회차).

    uv run python eval/pending18_rescue/measure_rescue.py    # GPU 불필요

1~4회차는 외양(색 히스토그램)으로 **하류를 기웠다.** 4회차가 그 아래를 열어
원인을 찾았다 — 갈아타는 프레임에서 진짜 대상은 사라진 게 아니라
`PERSON_ELIGIBLE_THRESHOLD = 0.5` 에 걸려 **버려졌다.** 후보 집합에 옳은 답이
없으면 어떤 외양 모델도 그것을 고를 수 없다.

이번에 바꾸는 것은 **한 곳뿐**이다. 이어가기에서 통과 후보로 **이미 실패했을
때만**(최고 IoU < `MIN_ANCHOR_IOU`) 밴드 `[0.3, 0.5)` 을 연다.

🔴 **새 상수가 0개다.** 0.3 은 production 검출 post-process(`pose.py:941`),
0.5 는 `PERSON_ELIGIBLE_THRESHOLD`, IoU 문턱은 `MIN_ANCHOR_IOU` 다. 1~3회차는
회차마다 상수를 더했고 **매번 그 상수가 문제였다**(`K` 가 41 ↔ 1).

규격은 `PREREGISTRATION.md`(커밋 `2cc290a`, 코드보다 먼저). 결과를 보고
상수를 고치지 않는다.

🔴 **`src/` 를 고치지 않는다.** 앞 회차 스크립트도 고치지 않는다 — 고치면
그 회차 결과와 비교가 끊긴다. import 만 한다.
"""
from __future__ import annotations

import csv
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_appearance"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_reacquire"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_conservative"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_scale"))

from labeling.targets import clip_ids, load_candidates  # noqa: E402
from measure_appearance import (  # noqa: E402
    BOXES,
    PERSON_THRESHOLD,
    SWITCHING,
    boxes_from_cache,
    hist_of,
    similarity,
)
from measure_conservative import (  # noqa: E402
    ALPHA,
    CALIBRATION,
    REACQ_K,
    REACQ_TAU,
    TAU,
    UPDATE_TAU,
    calibrate,
)
from measure_conservative import track as conservative_track  # noqa: E402
from measure_reacquire import CLIPS, anchor_of, wrong_and_cover  # noqa: E402
from measure_scale import MIN_MULTI_FRAMES, META, multi_frames, synthetic_anchor  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    MIN_ANCHOR_IOU,
    SubjectRequest,
    _iou,
    read_frames,
    select_subject_boxes,
)

# --- 사전 등록: 이번 회차가 쓰는 값은 전부 production 것이다 ---------------
LOW_MIN = 0.3          # = pose.py:941 검출 post-process. 캐시의 하한이기도 하다
LOW_MAX = PERSON_THRESHOLD   # = PERSON_ELIGIBLE_THRESHOLD (0.5). 이 위는 원래 통과한다
RESCUE_IOU = MIN_ANCHOR_IOU  # = 0.3. 「같은 사람인가」의 문턱은 production 에 이미 있다

# 4회차에서 커버 유지 50% 미만이던 넷 — 기준 D 는 **이 이름들**로 판정한다.
D_CLIPS = ["3R1kvNrGJK0", "6hrcRyIYTrA", "CFjNxCZhn_8", "bh6Cvz2orzQ"]

# 4회차가 센 상한 (사전 등록의 예측 대조용)
R4_RESCUABLE_FRAMES = 43
R4_RESCUABLE_CLIPS = 11


def low_from_cache(clip: str):
    """프레임별 **임계 미달** 후보 [(x, y, w, h, score)] — 밴드 [0.3, 0.5).

    🔴 새 검출이 아니다. production 이 이미 만들어 놓고 selector 가 버리는
    것이라, 이 처방은 구현도 값싸다 (재검출·GPU 불필요).
    """
    per_frame, _wh, _fps = load_candidates(clip)
    out, floor = [], 1.0
    for arr in per_frame:
        here = []
        for x1, y1, x2, y2, score in arr:
            s = float(score)
            floor = min(floor, s)
            if LOW_MIN <= s < LOW_MAX:
                here.append((float(x1), float(y1), float(x2 - x1), float(y2 - y1), s))
        out.append(here)
    return out, floor


def track_rescue(auto, cands, lows, frames, subject, fps, wh, K, *, rescue=True):
    """3회차 `track` + **구제**. 반환 (chosen, 재획득 횟수, 구제 기록).

    🔴 3회차에서 달라진 곳은 아래 「이번 회차의 유일한 변경」 블록 **하나**다.
    나머지는 그대로 옮겼다 — `rescue=False` 로 두면 3회차와 **완전히 같은
    출력**이 나와야 하고, main 이 25건 전수로 그것을 확인한다.
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, 0, []

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = seed
    reacquired = 0
    events: list[dict] = []

    def app(ref, t, box):
        if ref is None or box is None or t >= len(frames):
            return 1.0
        return similarity(ref, hist_of(frames[t], box))

    def walk(order, start):
        nonlocal reacquired
        previous, ref, lost, bad, good = start, ah, False, 0, 0
        for t in order:
            if not lost:
                pick, pick_iou = None, 0.0
                for cand in cands[t]:
                    iou = _iou(previous, cand)
                    if iou > pick_iou:
                        pick, pick_iou = cand, iou

                # --- 이번 회차의 유일한 변경 ---------------------------------
                # 🔴 통과 후보로 **이미 이어가기가 실패했을 때만** 연다.
                #    잘 겹치는 통과 후보가 있으면 고장난 것이 없으므로 손대지
                #    않는다 — 발동 빈도가 곧 위험의 상한이다.
                if rescue and pick_iou < RESCUE_IOU:
                    low, low_iou, low_score = None, 0.0, 0.0
                    for x, y, bw, bh, s in lows[t]:
                        iou = _iou(previous, (x, y, bw, bh))
                        if iou > low_iou:
                            low, low_iou, low_score = (x, y, bw, bh), iou, s
                    if low is not None and low_iou >= RESCUE_IOU:
                        events.append({
                            "t": t, "score": low_score, "iou_low": low_iou,
                            "iou_pass": pick_iou, "app": app(ah, t, low),
                        })
                        pick, pick_iou = low, low_iou
                # -------------------------------------------------------------

                if pick is None:
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
                    if a >= UPDATE_TAU and t < len(frames):
                        h = hist_of(frames[t], pick)
                        if h is not None and ref is not None:
                            ref = (1.0 - ALPHA) * ref + ALPHA * h
                chosen[t] = pick
                previous = pick
                continue

            # --- 잃은 상태: 외양으로 다시 찾는다 (구제를 쓰지 않는다) --------
            # 🔴 사전 등록: 재획득에는 구제를 넣지 않는다. 한 회차에 한 가지만
            #    바꾼다 — 둘을 함께 열면 좋아져도 무엇이 한 일인지 모른다.
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
                lost, bad, ref = False, 0, ah
                reacquired += 1
                chosen[t] = best
                previous = best
            else:
                chosen[t] = None

    walk(range(anchor + 1, n), seed)
    walk(range(anchor - 1, -1, -1), seed)
    return chosen, reacquired, events


def build_sample():
    """4회차와 **같은** 25건 — 표본 규칙을 바꾸지 않는다 (사전 등록)."""
    meta = {r["clip_id"]: r.get("single_or_multi", "").strip()
            for r in csv.DictReader(open(META, encoding="utf-8"))}
    sample = []
    for clip in clip_ids():   # 🔴 경로를 새로 쓰지 않는다 — targets.CAND 가 정한다
        if multi_frames(clip) < MIN_MULTI_FRAMES:
            continue
        if clip in BOXES:
            box, at_ms = BOXES[clip]
            sample.append((clip, box, at_ms, meta.get(clip, "?"), True))
        else:
            box, at_ms = synthetic_anchor(clip)
            if box is not None:
                sample.append((clip, box, at_ms, meta.get(clip, "?"), False))
    return sample


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    sample = build_sample()
    drawn = sum(1 for *_r, human in sample if human)
    print(f"표본 {len(sample)}건 — 사람이 그린 닻 {drawn}건 · 합성 닻 "
          f"{len(sample) - drawn}건 (4회차와 같은 규칙)\n")

    K = calibrate()
    print(f"→ K = {K}   (3·4회차와 **같은 규칙·같은 보정용 7건**. 구제는 보정에 "
          f"영향을 주지 않는다 — 보정은 production 출력을 걷는다)\n")

    rows, identical, cache_floor = [], True, 1.0
    all_events: list[tuple[str, dict]] = []
    print("═" * 104)
    print(f"  {'clip':16s} {'닻':4s} │ {'엉뚱:현':>7s} {'4회차':>6s} {'5회차':>6s} "
          f"{'감소4':>6s} {'감소5':>6s} │ {'커버4':>6s} {'커버5':>6s} │ {'구제':>4s}")
    print("═" * 104)

    for clip, box, at_ms, _ann, human in sample:
        auto, cands, wh, fps = boxes_from_cache(clip)
        lows, floor = low_from_cache(clip)
        cache_floor = min(cache_floor, floor)
        frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)
        base, _sel = select_subject_boxes(auto, cands, subject, fps, wh)
        anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        if anchor is None:
            print(f"  {clip:16s} {'사람' if human else '합성':4s} │ 닻 실패 — 건너뜀")
            continue

        r4, _rq4 = conservative_track(auto, cands, frames, subject, fps, wh, K)
        r5, _rq5, events = track_rescue(auto, cands, lows, frames, subject, fps, wh, K)

        # 🔴 자기 검사 — 구제를 끄면 3회차와 **완전히 같아야** 한다.
        off, _rq, off_ev = track_rescue(auto, cands, lows, frames, subject,
                                        fps, wh, K, rescue=False)
        if list(off) != list(r4) or off_ev:
            identical = False
            print(f"  🔴 {clip}: 구제를 꺼도 3회차와 다르다 — 옮겨 적기가 틀렸다")

        w0, c0 = wrong_and_cover(base, frames, ah)
        w4, c4 = wrong_and_cover(r4, frames, ah)
        w5, c5 = wrong_and_cover(r5, frames, ah)
        d4 = (1.0 - w4 / w0) if w0 else 0.0
        d5 = (1.0 - w5 / w0) if w0 else 0.0
        k4 = (c4 / c0) if c0 else 0.0
        k5 = (c5 / c0) if c0 else 0.0
        rows.append({"clip": clip, "human": human, "w0": w0, "w4": w4, "w5": w5,
                     "d4": d4, "d5": d5, "k4": k4, "k5": k5, "n_resc": len(events)})
        all_events += [(clip, e) for e in events]

        mark = " 🔴" if k5 < 0.50 else ("  ↑" if k4 < 0.50 <= k5 else "")
        print(f"  {clip:16s} {'사람' if human else '합성':4s} │ {w0:7d} {w4:6d} {w5:6d} "
              f"{d4:5.0%} {d5:5.0%} │ {k4:5.0%} {k5:5.0%}{mark} │ {len(events):4d}")

    by = {r["clip"]: r for r in rows}
    n = len(rows)

    print("\n" + "═" * 104)
    print("자기 검사 — 구제를 끄면 3회차와 같은가")
    print("═" * 104)
    print(f"  {'✅ 25건 전수 동일' if identical else '🔴 다르다'}"
          f"   (같으면 이번 결과의 차이는 **구제 하나**에서 온 것이다)")
    print(f"  캐시 점수 하한 실측 {cache_floor:.3f} — 사전 등록이 가정한 0.3 과 "
          f"{'일치' if abs(cache_floor - LOW_MIN) < 0.02 else '🔴 다르다'}")

    # --- 사전 등록이 보고하라고 한 다섯 ---------------------------------
    print("\n" + "═" * 104)
    print("사전 등록이 보고하라고 한 것")
    print("═" * 104)

    fired = [r for r in rows if r["n_resc"]]
    n_frames = sum(r["n_resc"] for r in rows)
    print(f"  2) 구제 발동 — **{n_frames}프레임 · {len(fired)}/{n}클립**")
    print(f"     예측: 4회차 상한 {R4_RESCUABLE_FRAMES}프레임 · "
          f"{R4_RESCUABLE_CLIPS}클립 이하 → "
          + ("✅ 예측대로다" if n_frames <= R4_RESCUABLE_FRAMES
             and len(fired) <= R4_RESCUABLE_CLIPS
             else "🔴 상한을 넘었다 — 게이트 구현을 의심해야 한다"))

    print("\n  3) 🔴 기준 D — 4회차에서 커버가 무너진 넷")
    print(f"     {'clip':16s} {'커버4':>6s} {'커버5':>6s} {'회복':>5s} │ "
          f"{'감소4':>6s} {'감소5':>6s} {'후퇴':>7s} │ 구제")
    recovered, regressed = [], []
    for clip in D_CLIPS:
        r = by.get(clip)
        if r is None:
            print(f"     {clip:16s} 표본에 없다 🔴")
            continue
        ok = r["k5"] >= 0.50
        back = r["d4"] - r["d5"]
        if ok:
            recovered.append(clip)
            if back > 0.10:
                regressed.append(clip)
        print(f"     {clip:16s} {r['k4']:5.0%} {r['k5']:5.0%} "
              f"{'  ✅' if ok else '  🔴':>5s} │ {r['d4']:5.0%} {r['d5']:5.0%} "
              f"{back:6.0%}{'🔴' if ok and back > 0.10 else '  '} │ {r['n_resc']}")

    worse = [r["clip"] for r in rows if r["w5"] > r["w0"]]
    new_low = [r["clip"] for r in rows
               if r["k5"] < 0.50 and r["clip"] not in D_CLIPS]
    print(f"\n  4) 엉뚱 프레임이 **는** 클립: {len(worse)}"
          + (f" — {', '.join(worse)}" if worse else " (없다)"))
    print(f"     D의 넷 밖에서 새로 커버 50% 미만: {len(new_low)}"
          + (f" — {', '.join(new_low)}" if new_low else " (없다)"))

    print("\n  5) 구제된 박스의 **닻 대비 외양 유사도** — 🔴 정황이지 정답이 아니다")
    if all_events:
        apps = sorted(e["app"] for _c, e in all_events)
        scores = [e["score"] for _c, e in all_events]
        ious = [e["iou_low"] for _c, e in all_events]
        print(f"     app  중앙 {st.median(apps):.2f} · 최소 {apps[0]:.2f} · "
              f"최대 {apps[-1]:.2f} · **≥{TAU} 인 것 "
              f"{sum(1 for a in apps if a >= TAU)}/{len(apps)}**")
        print(f"     점수 중앙 {st.median(scores):.2f} · IoU 중앙 "
              f"{st.median(ious):.2f} (버려진 통과 후보 IoU 중앙 "
              f"{st.median([e['iou_pass'] for _c, e in all_events]):.2f})")
    else:
        print("     구제가 한 번도 발동하지 않았다 🔴")

    print("\n  1) 전체 분포")
    for label, group in (("기존(사람 닻)", [r for r in rows if r["human"]]),
                         ("새로(합성 닻)", [r for r in rows if not r["human"]])):
        if not group:
            continue
        d5 = [r["d5"] for r in group if r["w0"]]
        k5 = [r["k5"] for r in group]
        print(f"     {label:14s} n={len(group):2d} · 엉뚱 감소 중앙 "
              f"{st.median(d5) if d5 else float('nan'):.0%} · 커버 유지 중앙 "
              f"{st.median(k5):.0%} · 커버<50% {sum(1 for k in k5 if k < 0.5)}건")

    # --- 합격 기준 -------------------------------------------------------
    a_ok = True
    for clip in sorted(BOXES):
        auto, cands, wh, fps = boxes_from_cache(clip)
        got, sel = select_subject_boxes(auto, cands, None, fps, wh)
        if got is not auto or sel.source != "auto":
            a_ok = False

    b_changed = []
    for clip in CALIBRATION:
        auto, cands, wh, fps = boxes_from_cache(clip)
        lows, _f = low_from_cache(clip)
        frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
        box, at_ms = BOXES[clip]
        subject = SubjectRequest(box=box, at_ms=at_ms)
        base, _sel = select_subject_boxes(auto, cands, subject, fps, wh)
        new, _rq, ev = track_rescue(auto, cands, lows, frames, subject, fps, wh, K)
        if list(new) != list(base):
            b_changed.append(f"{clip}({sum(1 for a, b in zip(new, base) if a != b)}프레임"
                             f"·구제{len(ev)})")

    c_hits = sum(1 for clip in sorted(SWITCHING)
                 if by.get(clip) and by[clip]["w0"] and by[clip]["d5"] >= 0.70)

    b_ok = not b_changed
    c_ok = c_hits >= 2
    d_ok = len(recovered) >= 3 and not regressed
    e_ok = len(worse) <= 2 and len(new_low) <= 1

    print("\n" + "═" * 104)
    print("사전 등록 합격 기준 (커밋 `2cc290a` — 결과를 보고 바꾸지 않았다)")
    print("═" * 104)
    print(f"  A 자동 경로 비트 동일 ………………………… {'✅ 만족' if a_ok else '🔴 불만족'}")
    print(f"  B 보정용 7건 기준선과 동일 ……………… {'✅ 만족' if b_ok else '🔴 불만족'}"
          + (f"   ({', '.join(b_changed)})" if b_changed else ""))
    print(f"  C 갈아탐 3건 엉뚱 70%+ 감소 2건+ … {'✅ 만족' if c_ok else '🔴 불만족'}"
          f"   ({c_hits}/3)")
    print(f"  D 무너진 넷 중 3건+ 커버 회복 ……… {'✅ 만족' if d_ok else '🔴 불만족'}"
          f"   (회복 {len(recovered)}/4"
          + (f", 후퇴 {', '.join(regressed)}" if regressed else "") + ")")
    print(f"  E 부수 피해 ………………………………………… {'✅ 만족' if e_ok else '🔴 불만족'}"
          f"   (엉뚱 증가 {len(worse)}건 ≤2 · 새 커버붕괴 {len(new_low)}건 ≤1)")

    print("\n" + "═" * 104)
    if a_ok and b_ok and c_ok and d_ok and e_ok:
        print("판정: **전 기준 만족.**")
    else:
        print("판정: **불합격.**")
    print("🔴 그래도 「고쳤다」가 아니다 — 구제된 박스가 진짜 대상인지는 라벨 없이")
    print("   말할 수 없고, 합성 닻은 「옳은 사람」이 아니다. 이 회차의 값은 **D**")
    print("   하나다: 4회차의 원인 진단(대상이 버려졌다)이 시험을 통과했는가.")
    print("🔴 이 회차도 `src/` 와 앞 회차 스크립트를 고치지 않았다.")


if __name__ == "__main__":
    main()
