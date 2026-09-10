#!/usr/bin/env python3
"""거부의 출력 형태 — 커버리지 붕괴 정면 (미결 18번 7회차).

    uv run python eval/pending18_coverage/measure_coverage.py    # GPU 불필요

3회차부터 「뿌리는 `K = 1` 거부」라고 적어 왔는데 **절반만 맞다.** `K` 는
얼마나 쉽게 거부하는가를 정하고, 거부한 **뒤에 무엇을 내놓는가**는 따로다.
커버리지를 0으로 만드는 것은 `chosen[t] = None` 이라는 **출력 형태**다.

같은 트래커가 「이 프레임의 대상을 모르겠다」에 **두 답**을 하고 있다 —
이어갈 후보가 없으면 `auto[t]` 로 떨어지고, 외양이 거부되면 `None` 이다.
6회차가 「재획득은 외양을 보는데 구제만 예외였다」를 고친 것과 같은 모양이라
**이번에도 문턱 추가가 아니라 불일치 제거다.** 새 상수는 0개.

🔴 **추적 결정은 한 비트도 안 바뀐다.** 채운 박스로 `previous`·`ref` 를
갱신하지 않으므로 거부·재획득·이어가기의 판단 순서가 6회차와 같다.
`fill=False` 로 두면 6회차와 **완전히 같은 출력**이 나와야 하고, main 이
전수로 확인한다.

✅ **순환성이 없다** — 채우기 결정이 `app` 을 보지 않는다. 그래서 6회차와
달리 프레임을 뺄 이유가 없고 **전 프레임으로 센다.** 대신 커버 분모가
커져 **엉뚱 절대 수는 반드시 는다** — 그래서 **엉뚱률로 짝지어 읽는다.**

규격은 `PREREGISTRATION.md`(커밋 `6b6a16a`, 코드보다 먼저).

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
            "eval/pending18_scale", "eval/pending18_rescue",
            "eval/pending18_gate"):
    sys.path.insert(0, str(ROOT / sub))

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
from measure_gate import GATE_TAU, track_gate  # noqa: E402
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import META, MIN_MULTI_FRAMES, RESCUE_IOU, low_from_cache  # noqa: E402
from measure_rescue import multi_frames, synthetic_anchor  # noqa: E402
from labeling.targets import clip_ids  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    SubjectRequest,
    _iou,
    read_frames,
    select_subject_boxes,
)

# --- 사전 등록: 새 상수가 0개다 -------------------------------------------
# 채우기는 문턱이 아니라 **형태**라 고를 값이 없다. 이것이 이 회차가
# 손잡이를 하나도 늘리지 않는 이유다.

# 🔴 6회차 기준선 — 사전 등록에 **결과를 보기 전에** 박아 둔 과녁이다.
#    (커버 <50% 인 7건. 주 4 + 보류 3.)
TARGET7 = ("CFjNxCZhn_8", "bh6Cvz2orzQ", "6hrcRyIYTrA", "3R1kvNrGJK0",
           "YNMHMKb5Md4", "gg5xRWjw3f8", "8gmHKqDxXdg")
COVER_BAR = 0.50     # C — 「붕괴」의 경계. 3회차 D 가 쓴 값 그대로다
RATE_BAR = 0.10      # D·E — 엉뚱률 10%p. 5·6회차 E 가 쓴 폭 그대로다
QUALITY_BAR = 0.50   # F — 채운 것의 절반 이상이 닻과 닮아야 한다


def track_fill(auto, cands, lows, frames, subject, fps, wh, K, *, fill=True):
    """6회차 `track_gate` + **거부해도 자동 박스로 떨어지기**.

    🔴 6회차에서 달라진 곳은 `_give_up` 세 자리뿐이다. `fill=False` 면
    6회차와 완전히 같은 출력이 나온다.

    반환: (chosen, reacquired, filled, unfillable)
      - `filled`     채운 프레임 번호 목록
      - `unfillable` 잃었는데 `auto[t]` 도 없어 못 채운 프레임 수
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, 0, [], 0

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = seed
    reacquired = 0
    filled: list[int] = []
    unfillable = 0

    def app(ref, t, box):
        if ref is None or box is None or t >= len(frames):
            return 1.0
        return similarity(ref, hist_of(frames[t], box))

    def give_up(t):
        """🔴 이 회차의 유일한 변경 — 「모르겠다」에 내놓는 것.

        🔴 `previous`·`ref` 를 **갱신하지 않는다.** 갱신하면 추적 결정이
        바뀌어 자기 검사가 성립하지 않는다 (사전 등록 「하지 않는 것」).
        """
        nonlocal unfillable
        if fill and auto[t] is not None:
            chosen[t] = auto[t]
            filled.append(t)
        else:
            chosen[t] = None
            if fill:
                unfillable += 1

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
                    low, low_iou = None, 0.0
                    for x, y, bw, bh, s in lows[t]:
                        iou = _iou(previous, (x, y, bw, bh))
                        if iou > low_iou:
                            low, low_iou = (x, y, bw, bh), iou
                    # 6회차의 구제 + 외양 문턱 — 그대로 둔다
                    if low is not None and low_iou >= RESCUE_IOU:
                        if app(ah, t, low) >= GATE_TAU:
                            pick, pick_iou = low, low_iou

                if pick is None:
                    # 🔴 원래부터 auto 로 떨어지던 자리다 — 안 건드린다
                    chosen[t] = auto[t]
                    if auto[t] is not None:
                        previous = auto[t]
                    continue
                a = app(ref, t, pick)
                if a < TAU:
                    bad += 1
                    if bad >= K:
                        lost, bad, good = True, 0, 0
                        give_up(t)          # ← 6회차: chosen[t] = None
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
                give_up(t)                  # ← 6회차: chosen[t] = None
                good = 0
                continue
            good += 1
            if good >= REACQ_K:
                lost, bad, ref = False, 0, ah
                reacquired += 1
                chosen[t] = best
                previous = best
            else:
                give_up(t)                  # ← 6회차: chosen[t] = None

    walk(range(anchor + 1, n), seed)
    walk(range(anchor - 1, -1, -1), seed)
    return chosen, reacquired, filled, unfillable


def wrong_and_cover(boxes, frames, ah):
    """(엉뚱, 커버) — 🔴 전 프레임. 순환성이 없어 뺄 프레임이 없다."""
    wrong = cover = 0
    for t, b in enumerate(boxes):
        if b is None:
            continue
        cover += 1
        if t < len(frames) and similarity(ah, hist_of(frames[t], b)) < TAU:
            wrong += 1
    return wrong, cover


def build_samples():
    """(주 표본 25건, 보류 표본 8건) — 5·6회차와 **같은 규칙**이다."""
    meta = {r["clip_id"]: r.get("single_or_multi", "").strip()
            for r in csv.DictReader(open(META, encoding="utf-8"))}
    main_s, held_s = [], []
    for clip in clip_ids():
        used = multi_frames(clip) >= MIN_MULTI_FRAMES
        if clip in BOXES:
            box, at_ms = BOXES[clip]
        else:
            box, at_ms = synthetic_anchor(clip)
        if box is None:
            continue
        row = (clip, box, at_ms, meta.get(clip, "?"))
        if used:
            main_s.append(row)
        elif clip not in BOXES:
            held_s.append(row)
    return main_s, held_s


def run_clip(clip, box, at_ms, K):
    """한 클립을 6회차·7회차로 돌리고 짝 지표를 낸다."""
    auto, cands, wh, fps = boxes_from_cache(clip)
    lows, _floor = low_from_cache(clip)
    frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
    subject = SubjectRequest(box=box, at_ms=at_ms)
    base, _sel = select_subject_boxes(auto, cands, subject, fps, wh)
    anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return None

    g6, _rq6, _ev6, _bl6 = track_gate(auto, cands, lows, frames, subject,
                                      fps, wh, K)
    off, _rqo, off_fill, _u = track_fill(auto, cands, lows, frames, subject,
                                         fps, wh, K, fill=False)
    r7, _rq7, filled, unfill = track_fill(auto, cands, lows, frames, subject,
                                          fps, wh, K)
    # 🔴 자기 검사: 채우기를 끄면 6회차와 완전히 같아야 한다.
    same = list(off) == list(g6) and not off_fill

    _w, c0 = wrong_and_cover(base, frames, ah)
    w6, c6 = wrong_and_cover(g6, frames, ah)
    w7, c7 = wrong_and_cover(r7, frames, ah)

    # 🔴 채운 것의 질 — 채운 박스가 닻과 닮았는가 (기준 F)
    fill_app = [similarity(ah, hist_of(frames[t], r7[t]))
                for t in filled if t < len(frames)]
    good_fill = sum(1 for v in fill_app if v >= TAU)
    return {
        "clip": clip, "self_ok": same,
        "w6": w6, "w7": w7, "c6": c6, "c7": c7,
        "k6": (c6 / c0) if c0 else 0.0, "k7": (c7 / c0) if c0 else 0.0,
        "r6": (w6 / c6) if c6 else 0.0, "r7": (w7 / c7) if c7 else 0.0,
        "filled": len(filled), "good_fill": good_fill, "unfill": unfill,
        "fill_app": fill_app,
    }


def _table(title, rows):
    print("\n" + "═" * 100)
    print(title)
    print("═" * 100)
    print(f"  {'clip':16s} │ {'커버6':>6s} {'커버7':>6s} │ "
          f"{'엉뚱률6':>7s} {'엉뚱률7':>7s} │ {'엉뚱6':>5s} {'엉뚱7':>5s} │ "
          f"{'채움':>5s} {'맞음':>5s} {'못참':>5s}")
    for r in rows:
        up = "  ↑" if r["k7"] > r["k6"] + 1e-9 else (
            " 🔴" if r["k7"] < r["k6"] - 1e-9 else "   ")
        bad = "🔴" if r["r7"] - r["r6"] >= RATE_BAR else "  "
        print(f"  {r['clip']:16s} │ {r['k6']:5.0%} {r['k7']:5.0%}{up} │ "
              f"{r['r6']:6.0%} {r['r7']:6.0%}{bad} │ {r['w6']:5d} {r['w7']:5d} │ "
              f"{r['filled']:5d} {r['good_fill']:5d} {r['unfill']:5d}")


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    main_s, held_s = build_samples()
    K = calibrate()
    print(f"주 표본 {len(main_s)}건 · 보류 표본 {len(held_s)}건 "
          f"(5·6회차와 같은 규칙)")
    print(f"→ K = {K}   (3~6회차와 같은 규칙·같은 보정용 7건)")
    print("🔴 엉뚱 절대 수는 **반드시 는다** — 채우면 분모가 커진다. "
          "짝은 엉뚱률이다 (사전 등록).")

    rows, self_fail = [], []
    for clip, box, at_ms, _ann in main_s:
        r = run_clip(clip, box, at_ms, K)
        if r is None:
            continue
        if not r["self_ok"]:
            self_fail.append(clip)
        rows.append(r)
    _table("주 표본 — 🔴 전 프레임으로 센다 (순환성 없음)", rows)

    held_rows = []
    for clip, box, at_ms, _ann in held_s:
        r = run_clip(clip, box, at_ms, K)
        if r is None:
            continue
        if not r["self_ok"]:
            self_fail.append(clip)
        held_rows.append(r)
    _table("🔴 보류 표본 — 1~5회차가 한 번도 안 쓴 클립", held_rows)

    everything = rows + held_rows
    by = {r["clip"]: r for r in everything}

    print("\n" + "═" * 100)
    print("자기 검사 — 채우기를 끄면 6회차와 같은가")
    print("═" * 100)
    print("  " + ("✅ 주·보류 전수 동일   (같으면 이번 차이는 **채우기 하나**에서 온 것이다)"
                  if not self_fail else "🔴 다르다: " + ", ".join(self_fail)))

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
        g6, _rq, _ev, _bl = track_gate(auto, cands, lows, frames, subject,
                                       fps, wh, K)
        new, _rq7, filled, _u = track_fill(auto, cands, lows, frames, subject,
                                           fps, wh, K)
        if list(new) != list(g6):
            n_diff = sum(1 for x, y in zip(new, g6) if x != y)
            b_changed.append(f"{clip}({n_diff}프레임·채움{len(filled)})")

    target = [by[c] for c in TARGET7 if c in by]
    recovered = [r for r in target if r["k7"] >= COVER_BAR]
    c_ok = len(recovered) >= 5

    rose = [r for r in target if r["k7"] > r["k6"] + 1e-9]
    d_bad = [r for r in rose if r["r7"] - r["r6"] >= RATE_BAR]
    d_ok = len(d_bad) <= 1

    keep = [r for r in everything if r["k6"] >= COVER_BAR]
    e_rate = [r for r in keep if r["r7"] - r["r6"] >= RATE_BAR]
    e_drop = [r for r in keep if r["k7"] < r["k6"] - 1e-9]
    e_ok = not e_rate and not e_drop

    n_fill = sum(r["filled"] for r in everything)
    n_good = sum(r["good_fill"] for r in everything)
    n_unfill = sum(r["unfill"] for r in everything)
    quality = (n_good / n_fill) if n_fill else 0.0
    f_ok = n_fill > 0 and quality >= QUALITY_BAR

    print("\n" + "═" * 100)
    print("사전 등록이 보고하라고 한 것 (판정에 쓰지 않는다)")
    print("═" * 100)
    reach = (n_fill / (n_fill + n_unfill)) if (n_fill + n_unfill) else 0.0
    print(f"  🔴 1) 잃은 프레임 중 `auto[t]` 가 있는 비율 — **{reach:.0%}** "
          f"(채움 {n_fill} · 못 채움 {n_unfill})")
    print("     이것이 낮으면 C 가 걸린 이유는 「채우기가 나쁘다」가 아니라")
    print("     **「채울 것이 애초에 없다」**다 — 다음 회차가 완전히 달라진다.")
    print(f"  2) 채운 것의 질 — {n_good}/{n_fill} = **{quality:.0%}** 가 `app(닻) >= {TAU}`")
    print(f"  3) 부 지표(엉뚱 절대 수) — 는 클립 "
          f"{sum(1 for r in everything if r['w7'] > r['w6'])}건 · 주는 클립 "
          f"{sum(1 for r in everything if r['w7'] < r['w6'])}건. "
          f"🔴 **후퇴로 읽지 않는다**")

    # 🔴 사후 관찰 — 사전 등록에 없다. **판정에 쓰지 않고 기준도 안 바꾼다.**
    #    F 가 걸린 이유를 둘로 가른다: 채운 것이 **남**인가, 아니면 **대상인데
    #    app 이 못 알아본 것**인가. 둘은 다음 회차를 완전히 다른 곳으로 보낸다.
    app_all = sorted(v for r in everything for v in r["fill_app"])
    if app_all:
        q = st.quantiles(app_all, n=4) if len(app_all) >= 4 else [0, 0, 0]
        near = sum(1 for v in app_all if 0.5 <= v < TAU)
        print(f"\n  🔴 사후 관찰 (사전 등록에 없다 — 판정에 쓰지 않는다)")
        print(f"     채운 프레임의 app 분포 — 중앙 **{st.median(app_all):.2f}** · "
              f"1사분 {q[0]:.2f} · 3사분 {q[2]:.2f} · 최대 {max(app_all):.2f}")
        print(f"     문턱 바로 아래(0.50 ≤ app < {TAU})는 **{near}/{len(app_all)} "
              f"= {near / len(app_all):.0%}**")
        print("     🔴 분포가 문턱에 붙어 있으면 「대상인데 못 알아본 것」이고,")
        print("        멀리 떨어져 있으면 「남을 채운 것」이다.")

    print("\n" + "═" * 100)
    print("사전 등록 합격 기준 (커밋 `6b6a16a` — 결과를 보고 바꾸지 않았다)")
    print("═" * 100)
    print(f"  A 자동 경로 비트 동일 ……………………………… {'✅ 만족' if a_ok else '🔴 불만족'}")
    print(f"  B 보정용 7건이 6회차와 비트 동일 ……………… {'✅ 만족' if not b_changed else '🔴 불만족'}"
          + (f"   ({', '.join(b_changed)})" if b_changed else ""))
    print(f"  C 과녁 7건 중 5건+ 이 커버 50%+ ……………… {'✅ 만족' if c_ok else '🔴 불만족'}"
          f"   ({len(recovered)}/{len(target)}건"
          + (f": {', '.join(r['clip'] for r in recovered)}" if recovered else "") + ")")
    print(f"  D 짝 — 커버 오른 클립의 엉뚱률 10%p+ ≤1건 … {'✅ 만족' if d_ok else '🔴 불만족'}"
          f"   (오른 {len(rose)}건 중 {len(d_bad)}건"
          + (f": {', '.join(r['clip'] for r in d_bad)}" if d_bad else "") + ")")
    print(f"  E 대가 — 커버 ≥50% 였던 {len(keep):2d}건 지킴 ………… {'✅ 만족' if e_ok else '🔴 불만족'}"
          f"   (엉뚱률 후퇴 {len(e_rate)}건 · 커버 하락 {len(e_drop)}건"
          + (f": {', '.join(r['clip'] for r in e_rate + e_drop)}"
             if (e_rate or e_drop) else "") + ")")
    print(f"  F 채운 것의 질 절반+ ……………………………… {'✅ 만족' if f_ok else '🔴 불만족'}"
          f"   ({quality:.0%})")

    core = [a_ok, not b_changed, c_ok, d_ok, e_ok, f_ok]
    print("\n" + "═" * 100)
    print("판정: " + ("**전 기준 만족.**" if all(core) else "**불합격.**"))
    print("🔴 「고쳤다」가 아니다 — 채운 박스가 진짜 대상인지는 **라벨 없이 못")
    print("   말한다.** `app(닻)` 은 대리 지표고, 보류 8건은 전부 합성 닻이다.")
    print("🔴 커버리지가 오르는 것 자체는 성과가 아니다 — 전부 채우면 100%다.")
    print("   그래서 D·F 를 짝으로 박아 두었다.")
    print("🔴 `src/` 와 앞 회차 스크립트를 고치지 않았다.")


if __name__ == "__main__":
    main()
