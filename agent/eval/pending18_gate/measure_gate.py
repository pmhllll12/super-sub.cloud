#!/usr/bin/env python3
"""구제 시점의 외양 문턱 — 불일치를 없앤다 (미결 18번 6회차).

    uv run python eval/pending18_gate/measure_gate.py    # GPU 불필요

5회차의 구제는 **IoU 만 보고 외양을 안 봤다.** 같은 트래커에서 재획득은
이미 닻 대비 `app >= REACQ_TAU` 를 요구하는데 **구제만 예외**였고, 그
예외가 `CFjNxCZhn_8` 을 망가뜨렸다(엉뚱 35 → 213, 그 구제의 app 0.55).

이번에 바꾸는 것은 하나다 — **구제된 박스도 닻 대비 `app >= TAU` 를 넘어야
한다.** 새 상수는 0개다(`TAU` 는 3회차 상수, `REACQ_TAU` 와 같은 값).

🔴 **순환성.** 「엉뚱」의 정의가 `app(닻) < TAU` 라 이 문턱과 같은 양을 쓴다.
그대로 두면 구제된 프레임은 정의상 엉뚱일 수 없어 지표가 공짜로 좋아진다.
그래서 **주 지표는 구제된 프레임을 뺀 엉뚱 수**이고, 같은 프레임 번호를
기준선·5회차·6회차 셋 다에서 똑같이 뺀다.

규격은 `PREREGISTRATION.md`(커밋 `1a4722c`, 코드보다 먼저).

🔴 **`src/` 와 앞 회차 스크립트를 고치지 않는다.** import 만 한다.
"""
from __future__ import annotations

import csv
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("src", "eval/phaseA", "eval/pending18_appearance",
            "eval/pending18_reacquire", "eval/pending18_conservative",
            "eval/pending18_scale", "eval/pending18_rescue"):
    sys.path.insert(0, str(ROOT / sub))

from labeling.targets import clip_ids  # noqa: E402
from measure_appearance import BOXES, boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_conservative import (  # noqa: E402
    ALPHA,
    CALIBRATION,
    REACQ_K,
    REACQ_TAU,
    TAU,
    UPDATE_TAU,
    calibrate,
)
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import META, MIN_MULTI_FRAMES, RESCUE_IOU, low_from_cache  # noqa: E402
from measure_rescue import multi_frames, synthetic_anchor  # noqa: E402
from measure_rescue import track_rescue as track_r5  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    SubjectRequest,
    _iou,
    read_frames,
    select_subject_boxes,
)

# --- 사전 등록: 이번에도 새 상수가 0개다 ----------------------------------
GATE_TAU = TAU   # = REACQ_TAU = 0.6. 재획득이 이미 요구하는 것을 구제에도 건다

# 5회차가 낸 값 — 기준 C·D 는 **이 이름과 수**로 판정한다.
C_CLIP, C_WRONG5, C_KEEP5 = "X6dC9pu5H3k", 0, 1.00
D_CLIP, D_WRONG4 = "CFjNxCZhn_8", 35


def track_gate(auto, cands, lows, frames, subject, fps, wh, K, *, gate=True):
    """5회차 `track_rescue` + **구제 시점 외양 문턱**.

    🔴 5회차에서 달라진 곳은 「이번 회차의 유일한 변경」 블록 하나다.
    `gate=False` 로 두면 5회차와 **완전히 같은 출력**이 나와야 하고,
    main 이 전수로 그것을 확인한다.
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, 0, [], []

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = seed
    reacquired = 0
    events: list[dict] = []
    blocked: list[dict] = []

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

                if pick_iou < RESCUE_IOU:
                    low, low_iou, low_score = None, 0.0, 0.0
                    for x, y, bw, bh, s in lows[t]:
                        iou = _iou(previous, (x, y, bw, bh))
                        if iou > low_iou:
                            low, low_iou, low_score = (x, y, bw, bh), iou, s
                    if low is not None and low_iou >= RESCUE_IOU:
                        a_anchor = app(ah, t, low)
                        rec = {"t": t, "score": low_score, "iou_low": low_iou,
                               "iou_pass": pick_iou, "app": a_anchor}
                        # --- 이번 회차의 유일한 변경 -------------------------
                        # 🔴 재획득은 닻 대비 app >= REACQ_TAU 를 요구한다.
                        #    구제만 예외일 이유가 없다 — 문턱 추가가 아니라
                        #    불일치 제거다.
                        if gate and a_anchor < GATE_TAU:
                            blocked.append(rec)
                        else:
                            events.append(rec)
                            pick, pick_iou = low, low_iou
                        # -----------------------------------------------------

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

            # --- 잃은 상태: 재획득 (구제를 쓰지 않는다 — 5회차에서 닫힌 경로)
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
    return chosen, reacquired, events, blocked


def wrong_and_cover_excluding(boxes, frames, ah, skip: set[int]):
    """🔴 주 지표 — **구제된 프레임을 뺀** (엉뚱, 커버).

    `skip` 은 세 회차에서 **같은 프레임 번호**를 뺀다. 문턱이 지표와 같은
    양을 쓰므로, 빼지 않으면 구제된 프레임이 정의상 엉뚱일 수 없어 공짜로
    좋아진다 (사전 등록 「순환성」 절).
    """
    wrong = cover = 0
    for t, b in enumerate(boxes):
        if t in skip or b is None:
            continue
        cover += 1
        if t < len(frames) and similarity(ah, hist_of(frames[t], b)) < TAU:
            wrong += 1
    return wrong, cover


def build_samples():
    """(주 표본 25건, 보류 표본) — 주 표본은 5회차와 **같은 규칙**이다.

    🔴 보류 표본에 새 컷을 만들지 않는다. 「1~5회차가 안 쓴 것」 중
    **기존 닻 규칙이 통과시키는 것 전부**다.
    """
    meta = {r["clip_id"]: r.get("single_or_multi", "").strip()
            for r in csv.DictReader(open(META, encoding="utf-8"))}
    main_s, held_s = [], []
    for clip in clip_ids():
        used = multi_frames(clip) >= MIN_MULTI_FRAMES
        if clip in BOXES:
            box, at_ms, human = *BOXES[clip], True
        else:
            box, at_ms = synthetic_anchor(clip)
            human = False
        if box is None:
            continue
        row = (clip, box, at_ms, meta.get(clip, "?"), human)
        if used:
            main_s.append(row)
        elif clip not in BOXES:      # BOXES 10건은 보정용·시험용으로 이미 쓴다
            held_s.append(row)
    return main_s, held_s


def run_clip(clip, box, at_ms, K):
    """한 클립을 3회차·5회차·6회차로 각각 돌리고 주 지표를 낸다."""
    auto, cands, wh, fps = boxes_from_cache(clip)
    lows, _floor = low_from_cache(clip)
    frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
    subject = SubjectRequest(box=box, at_ms=at_ms)
    base, _sel = select_subject_boxes(auto, cands, subject, fps, wh)
    anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return None

    r5, _rq5, ev5 = track_r5(auto, cands, lows, frames, subject, fps, wh, K)
    r6, _rq6, ev6, blocked = track_gate(auto, cands, lows, frames, subject,
                                        fps, wh, K)
    off, _rq, off_ev, off_bl = track_gate(auto, cands, lows, frames, subject,
                                          fps, wh, K, gate=False)
    # 🔴 자기 검사: 문턱을 끄면 5회차와 완전히 같아야 한다.
    same = list(off) == list(r5) and not off_bl and len(off_ev) == len(ev5)

    # 🔴 주 지표: 어느 회차에서든 구제가 걸린 프레임은 셋 다에서 뺀다.
    skip = {e["t"] for e in ev5} | {e["t"] for e in ev6} | {e["t"] for e in blocked}
    w0, c0 = wrong_and_cover_excluding(base, frames, ah, skip)
    w5, c5 = wrong_and_cover_excluding(r5, frames, ah, skip)
    w6, c6 = wrong_and_cover_excluding(r6, frames, ah, skip)
    # 부 지표: 전체 (판정에 쓰지 않는다)
    a0, _ = wrong_and_cover_excluding(base, frames, ah, set())
    a5, _ = wrong_and_cover_excluding(r5, frames, ah, set())
    a6, _ = wrong_and_cover_excluding(r6, frames, ah, set())
    return {
        "clip": clip, "self_ok": same,
        "w0": w0, "w5": w5, "w6": w6, "c0": c0, "c5": c5, "c6": c6,
        "all0": a0, "all5": a5, "all6": a6,
        "n5": len(ev5), "n6": len(ev6), "nblock": len(blocked),
        "blocked": blocked, "kept": ev6,
        "k5": (c5 / c0) if c0 else 0.0, "k6": (c6 / c0) if c0 else 0.0,
        "d5": (1.0 - w5 / w0) if w0 else 0.0,
        "d6": (1.0 - w6 / w0) if w0 else 0.0,
    }


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    main_s, held_s = build_samples()
    print(f"주 표본 {len(main_s)}건 (5회차와 같은 규칙) · "
          f"🔴 보류 표본 {len(held_s)}건 — **1~5회차가 한 번도 안 쓴 것**\n"
          f"   보류: {', '.join(c for c, *_r in held_s)}\n")

    K = calibrate()
    print(f"→ K = {K}   (3~5회차와 같은 규칙·같은 보정용 7건)\n")

    print("═" * 108)
    print("주 표본 — 🔴 엉뚱은 **구제된 프레임을 뺀** 주 지표다 (순환성 처리)")
    print("═" * 108)
    print(f"  {'clip':16s} │ {'엉뚱:현':>7s} {'5회차':>6s} {'6회차':>6s} │ "
          f"{'커버5':>6s} {'커버6':>6s} │ {'구제5':>5s} {'구제6':>5s} {'막힘':>4s}")
    rows, self_fail = [], []
    for clip, box, at_ms, _ann, _human in main_s:
        r = run_clip(clip, box, at_ms, K)
        if r is None:
            print(f"  {clip:16s} │ 닻 실패 — 건너뜀")
            continue
        if not r["self_ok"]:
            self_fail.append(clip)
        rows.append(r)
        flag = ""
        if r["w6"] > r["w5"]:
            flag = " 🔴"
        elif r["w6"] < r["w5"]:
            flag = "  ↑"
        print(f"  {clip:16s} │ {r['w0']:7d} {r['w5']:6d} {r['w6']:6d}{flag} │ "
              f"{r['k5']:5.0%} {r['k6']:5.0%} │ {r['n5']:5d} {r['n6']:5d} "
              f"{r['nblock']:4d}")

    by = {r["clip"]: r for r in rows}

    print("\n" + "═" * 108)
    print("자기 검사 — 문턱을 끄면 5회차와 같은가")
    print("═" * 108)
    print(f"  {'✅ 주 표본 전수 동일' if not self_fail else '🔴 다르다: ' + ', '.join(self_fail)}"
          f"   (같으면 이번 차이는 **문턱 하나**에서 온 것이다)")

    # --- 보류 표본 -------------------------------------------------------
    print("\n" + "═" * 108)
    print("🔴 보류 표본 — 1~5회차가 한 번도 안 쓴 클립")
    print("═" * 108)
    held_rows = []
    if not held_s:
        print("  닻이 만들어지는 클립이 없다")
    else:
        # 🔴 커버5 도 함께 낸다 — F 가 걸릴 경우 **문턱 때문인지** 아니면
        #    이미 있던 커버리지 붕괴 때문인지 갈라야 한다. (기준은 안 바꾼다.)
        print(f"  {'clip':16s} │ {'엉뚱:현':>7s} {'5회차':>6s} {'6회차':>6s} │ "
              f"{'커버5':>6s} {'커버6':>6s} │ {'구제5':>5s} {'구제6':>5s} {'막힘':>4s}")
        for clip, box, at_ms, _ann, _human in held_s:
            r = run_clip(clip, box, at_ms, K)
            if r is None:
                print(f"  {clip:16s} │ 닻 실패 — 건너뜀")
                continue
            held_rows.append(r)
            gate_did = "" if (r["k6"] == r["k5"] and r["w6"] == r["w5"]) else " ←문턱"
            print(f"  {clip:16s} │ {r['w0']:7d} {r['w5']:6d} {r['w6']:6d} │ "
                  f"{r['k5']:5.0%} {r['k6']:5.0%} │ {r['n5']:5d} {r['n6']:5d} "
                  f"{r['nblock']:4d}{gate_did}")

    held_fired = sum(r["n6"] + r["nblock"] for r in held_rows)
    held_worse = [r["clip"] for r in held_rows if r["w6"] > r["w0"]]
    held_lowcov = [r["clip"] for r in held_rows if r["k6"] < 0.50]

    # --- 기준 ------------------------------------------------------------
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
        new, _rq, ev, bl = track_gate(auto, cands, lows, frames, subject,
                                      fps, wh, K)
        if list(new) != list(base):
            b_changed.append(f"{clip}({sum(1 for x, y in zip(new, base) if x != y)}프레임"
                             f"·구제{len(ev)}·막힘{len(bl)})")

    c = by.get(C_CLIP)
    c_ok = bool(c) and c["w6"] <= C_WRONG5 and c["k6"] >= C_KEEP5 - 1e-9
    d = by.get(D_CLIP)
    d_ok = bool(d) and d["w6"] <= D_WRONG4

    # E — 5회차에서 구제로 좋아졌던 클립이 6회차에 후퇴하는가 (직전 회차 대비)
    improved5 = [r for r in rows if r["n5"] and r["w5"] < r["w0"]]
    regress = []
    for r in improved5:
        if not r["w0"]:
            continue
        back = (r["w6"] - r["w5"]) / r["w0"]
        if back >= 0.10:
            regress.append((r["clip"], back))
    e_ok = len(regress) <= 1

    print("\n" + "═" * 108)
    print("사전 등록이 보고하라고 한 것")
    print("═" * 108)
    n_block = sum(r["nblock"] for r in rows)
    n_keep = sum(r["n6"] for r in rows)
    print(f"  막힌 구제 **{n_block}** · 통과한 구제 **{n_keep}** "
          f"(5회차 {sum(r['n5'] for r in rows)}회)")
    print(f"     예측 「20회 안팎이 막힌다」 → "
          + ("✅ 그 언저리다" if 14 <= n_block <= 26 else "🔴 빗나갔다"))

    print(f"\n  🔴 기준 E — 5회차에서 구제로 좋아졌던 {len(improved5)}건의 행방")
    print(f"     {'clip':16s} {'엉뚱5':>6s} {'엉뚱6':>6s} {'후퇴':>7s}  구제5→6(막힘)")
    for r in improved5:
        back = (r["w6"] - r["w5"]) / r["w0"] if r["w0"] else 0.0
        print(f"     {r['clip']:16s} {r['w5']:6d} {r['w6']:6d} {back:6.0%}"
              f"{'🔴' if back >= 0.10 else '  '}  {r['n5']}→{r['n6']}({r['nblock']})")

    allblocked = [e for r in rows for e in r["blocked"]]
    allkept = [e for r in rows for e in r["kept"]]
    if allblocked:
        print(f"\n  막힌 구제의 app 분포 — 중앙 "
              f"{st.median([e['app'] for e in allblocked]):.2f} · 최대 "
              f"{max(e['app'] for e in allblocked):.2f}")
    if allkept:
        print(f"  통과한 구제의 app 분포 — 중앙 "
              f"{st.median([e['app'] for e in allkept]):.2f} · 최소 "
              f"{min(e['app'] for e in allkept):.2f}")

    print(f"\n  부 지표(전체 프레임, 판정에 쓰지 않는다) — 6회차가 5회차보다 "
          f"엉뚱이 적은 클립 {sum(1 for r in rows if r['all6'] < r['all5'])}건 · "
          f"많은 클립 {sum(1 for r in rows if r['all6'] > r['all5'])}건")

    print("\n" + "═" * 108)
    print("사전 등록 합격 기준 (커밋 `1a4722c` — 결과를 보고 바꾸지 않았다)")
    print("═" * 108)
    print(f"  A 자동 경로 비트 동일 ……………………………… {'✅ 만족' if a_ok else '🔴 불만족'}")
    print(f"  B 보정용 7건 비트 동일 …………………………… {'✅ 만족' if not b_changed else '🔴 불만족'}"
          + (f"   ({', '.join(b_changed)})" if b_changed else ""))
    print(f"  C {C_CLIP} 성과 유지 ……………… {'✅ 만족' if c_ok else '🔴 불만족'}"
          + (f"   (엉뚱 {c['w6']}, 커버 {c['k6']:.0%})" if c else "   (표본에 없다)"))
    print(f"  D {D_CLIP} 후퇴 사라짐 ………… {'✅ 만족' if d_ok else '🔴 불만족'}"
          + (f"   (엉뚱 {d['w6']} ≤ {D_WRONG4})" if d else "   (표본에 없다)"))
    print(f"  E 대가 — 10%p+ 후퇴 ≤1건 ………………………… {'✅ 만족' if e_ok else '🔴 불만족'}"
          f"   ({len(regress)}건"
          + (f": {', '.join(c for c, _b in regress)}" if regress else "") + ")")
    if held_fired == 0:
        print("  F 보류 표본 ……………………………………………… ⚠️ **판정하지 않는다** — "
              "구제가 0회 발동했다")
        print("     🔴 발동 0회를 「부작용 없음 ✅」으로 적지 않는다 (사전 등록).")
        f_ok = None
    else:
        f_ok = not held_worse and len(held_lowcov) <= 1
        print(f"  F 보류 표본 ……………………………………………… {'✅ 만족' if f_ok else '🔴 불만족'}"
              f"   (발동 {held_fired}회 · 엉뚱 증가 {len(held_worse)}건 · "
              f"커버<50% {len(held_lowcov)}건)")
        # 🔴 F 가 걸렸으면 **문턱 탓인지** 갈라서 적는다 (기준은 안 바꾼다).
        gate_caused = [r["clip"] for r in held_rows
                       if r["k6"] < 0.50 <= r["k5"]]
        if held_lowcov:
            print(f"     커버<50%: {', '.join(held_lowcov)}")
            print(f"     그중 **문턱이 떨어뜨린 것**: "
                  + (", ".join(gate_caused) if gate_caused else "**없다** — "
                     "문턱을 꺼도(5회차) 이미 50% 미만이다"))

    core = [a_ok, not b_changed, c_ok, d_ok, e_ok] + ([f_ok] if f_ok is not None else [])
    print("\n" + "═" * 108)
    print("판정: " + ("**전 기준 만족.**" if all(core) else "**불합격.**"))
    print("🔴 C·D 는 5회차 데이터에서 이미 예측 가능했다 — 만족해도 **증거로 치지")
    print("   않는다**(사전 등록). 이 회차의 값은 **E·B·F** 에 있다.")
    print("🔴 「고쳤다」가 아니다 — 구제된 박스가 진짜 대상인지는 라벨 없이 못")
    print("   말하고, 합성 닻은 「옳은 사람」이 아니다.")
    print("🔴 `src/` 와 앞 회차 스크립트를 고치지 않았다.")


if __name__ == "__main__":
    main()
