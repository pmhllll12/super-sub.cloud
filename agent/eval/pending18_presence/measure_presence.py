#!/usr/bin/env python3
"""잃은 구간에 **대상이 있기는 한가** (미결 18번 8회차).

    uv run python eval/pending18_presence/measure_presence.py    # GPU 불필요

3~7회차가 다섯 번 처방을 냈고 다섯 번 다 불합격이었다. **매 회차가 앞 회차의
진단을 정정했다.** 여섯 번째 처방을 내기 전에 **고치려는 것이 결함이기는
한지**를 먼저 잰다.

🔴 **이 회차는 읽기만 한다.** 궤적은 6회차 `track_gate` 그대로이고, 여기
`track_traced` 는 같은 코드에 **상태 기록만** 더한 사본이다. main 이 전수로
`chosen` 비트 동일을 확인한다 — 다르면 이 회차의 숫자가 다른 궤적의 것이다.

🔴 **대조군이 이 회차의 핵심이다.** 7회차의 「채운 프레임 app 중앙 0.28」은
그 숫자만으로 아무것도 안 말한다. 같은 클립이 **잘 될 때** 얼마가 나오는지를
함께 재야 「대상이 아니다」와 「기술자가 못 쓴다」가 갈린다.

규격은 `PREREGISTRATION.md`(커밋 `60d2673`, 코드보다 먼저).

🔴 **`src/` 와 앞 회차 스크립트를 고치지 않는다. 새 상수도 0개다.**
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("src", "eval/phaseA", "eval/pending18_appearance",
            "eval/pending18_reacquire", "eval/pending18_conservative",
            "eval/pending18_scale", "eval/pending18_rescue",
            "eval/pending18_gate", "eval/pending18_coverage"):
    sys.path.insert(0, str(ROOT / sub))

from measure_appearance import boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_conservative import (  # noqa: E402
    ALPHA, REACQ_K, REACQ_TAU, TAU, UPDATE_TAU, calibrate,
)
from measure_coverage import TARGET7, build_samples  # noqa: E402
from measure_gate import GATE_TAU, track_gate  # noqa: E402
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import RESCUE_IOU, low_from_cache  # noqa: E402
from supersub_agent.pose import SubjectRequest, _iou, read_frames  # noqa: E402

# --- 사전 등록: 새 상수가 0개다 -------------------------------------------
# 「같은 사람인가」의 공간 문턱은 RESCUE_IOU(= production MIN_ANCHOR_IOU = 0.3),
# 「닮았는가」의 외양 문턱은 TAU(= REACQ_TAU = GATE_TAU = 0.6). 둘 다 이미 있다.
DOMINANT = 0.70    # 한 갈래로 몰렸다고 볼 비율 (사전 등록 「판정」)
PROXY_FAIL = 4     # 이만큼이 proxy_unusable 이면 판별불가 (7건 중)


def track_traced(auto, cands, lows, frames, subject, fps, wh, K):
    """6회차 `track_gate` **그대로** + 프레임별 상태·직전 박스 기록.

    🔴 판단 흐름을 한 줄도 안 바꿨다. 더한 것은 `state`·`prev_box` 기록뿐이고,
    main 이 `chosen` 을 `track_gate` 와 비교해 그것을 확인한다.

    반환: (chosen, state, prev_box)
      state[t] ∈ {"anchor","pick","auto","lost","reacq", None}
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, [None] * n, [None] * n

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    state: list[str | None] = [None] * n
    prev_box: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = seed
    state[anchor] = "anchor"

    def app(ref, t, box):
        if ref is None or box is None or t >= len(frames):
            return 1.0
        return similarity(ref, hist_of(frames[t], box))

    def walk(order, start):
        previous, ref, lost, bad, good = start, ah, False, 0, 0
        for t in order:
            prev_box[t] = previous
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
                    if low is not None and low_iou >= RESCUE_IOU:
                        if app(ah, t, low) >= GATE_TAU:
                            pick, pick_iou = low, low_iou

                if pick is None:
                    chosen[t] = auto[t]
                    state[t] = "auto"
                    if auto[t] is not None:
                        previous = auto[t]
                    continue
                a = app(ref, t, pick)
                if a < TAU:
                    bad += 1
                    if bad >= K:
                        lost, bad, good = True, 0, 0
                        chosen[t] = None
                        state[t] = "lost"
                        continue
                else:
                    bad = 0
                    if a >= UPDATE_TAU and t < len(frames):
                        h = hist_of(frames[t], pick)
                        if h is not None and ref is not None:
                            ref = (1.0 - ALPHA) * ref + ALPHA * h
                chosen[t] = pick
                state[t] = "pick"
                previous = pick
                continue

            best, best_app = None, REACQ_TAU
            for cand in cands[t]:
                v = app(ah, t, cand)
                if v >= best_app:
                    best, best_app = cand, v
            if best is None:
                chosen[t] = None
                state[t] = "lost"
                good = 0
                continue
            good += 1
            if good >= REACQ_K:
                lost, bad, ref = False, 0, ah
                chosen[t] = best
                state[t] = "reacq"
                previous = best
            else:
                chosen[t] = None
                state[t] = "lost"

    walk(range(anchor + 1, n), seed)
    walk(range(anchor - 1, -1, -1), seed)
    return chosen, state, prev_box


def lost_runs(state):
    """연속된 `lost` 구간 [(시작, 끝), ...]. 끝은 포함이다."""
    runs, s = [], None
    for t, v in enumerate(state):
        if v == "lost":
            if s is None:
                s = t
        elif s is not None:
            runs.append((s, t - 1))
            s = None
    if s is not None:
        runs.append((s, len(state) - 1))
    return runs


def classify(run, cands, lows, frames, ah, prev_box, anchor):
    """사전 등록의 매핑 — **순서대로 먼저 맞는 것**을 취한다."""
    s, e = run
    # 잃은 구간 내내 `previous` 는 고정이다(재획득 전까지 갱신되지 않는다).
    # walk 가 먼저 닿는 끝에서 읽는다 — 앞쪽 구간은 뒤에서, 뒤쪽은 앞에서다.
    prev = prev_box[s] if s > anchor else prev_box[e]

    n_cand, cont, apps = [], [], []
    for t in range(s, e + 1):
        pool = list(cands[t]) + [(x, y, bw, bh) for x, y, bw, bh, _s in lows[t]]
        n_cand.append(len(cands[t]))
        cont.append(max((_iou(prev, c) for c in pool), default=0.0)
                    if prev is not None else 0.0)
        apps.append(max((app_of(ah, t, c, frames) for c in pool), default=0.0))

    med = lambda v: st.median(v) if v else 0.0  # noqa: E731
    n_med, cont_med, app_med = med(n_cand), med(cont), med(apps)

    if n_med == 0:
        kind = "absent"
    elif cont_med < RESCUE_IOU:
        kind = "drifted_away"
    elif app_med < TAU:
        kind = "rejected"
    else:
        kind = "unexplained"
    return {
        "run": run, "len": e - s + 1, "kind": kind,
        "n_cand": n_med, "cont_iou": cont_med, "app_lost": app_med,
        "t_from_anchor": min(abs(s - anchor), abs(e - anchor)),
    }


def app_of(ah, t, box, frames):
    if box is None or t >= len(frames):
        return 0.0
    h = hist_of(frames[t], box)
    return similarity(ah, h) if h is not None else 0.0


def run_clip(clip, box, at_ms, K):
    auto, cands, wh, fps = boxes_from_cache(clip)
    lows, _floor = low_from_cache(clip)
    frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
    subject = SubjectRequest(box=box, at_ms=at_ms)
    anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return None

    g6, _rq, _ev, _bl = track_gate(auto, cands, lows, frames, subject, fps, wh, K)
    chosen, state, prev_box = track_traced(auto, cands, lows, frames,
                                           subject, fps, wh, K)
    same = list(chosen) == list(g6)      # 자기 검사 A

    # 🔴 대조군 — 트래커가 **안 잃고 따라가는** 프레임의 app(닻, chosen[t]).
    #    `auto` 로 떨어진 프레임은 추적한 것이 아니라 뺀다.
    clean = [app_of(ah, t, chosen[t], frames)
             for t, v in enumerate(state) if v in ("pick", "reacq", "anchor")]
    clean_med = st.median(clean) if clean else 0.0
    clean_ncand = [len(cands[t]) for t, v in enumerate(state)
                   if v in ("pick", "reacq", "anchor")]

    runs = [classify(r, cands, lows, frames, ah, prev_box, anchor)
            for r in lost_runs(state)]
    lost_n = sum(r["len"] for r in runs)

    # 대조군 관문 — 잘 될 때도 안 닮으면 `rejected` 로 읽지 않는다.
    proxy_ok = clean_med >= TAU
    if not proxy_ok:
        for r in runs:
            if r["kind"] == "rejected":
                r["kind"] = "proxy_unusable"

    # 자기 검사 C — 잃은 프레임 중 auto[t] 가 있는 비율 (7회차 93% 재현)
    has_auto = sum(1 for t, v in enumerate(state)
                   if v == "lost" and auto[t] is not None)

    return {
        "clip": clip, "self_ok": same, "anchor": anchor, "n": len(auto),
        "clean_med": clean_med, "clean_n": len(clean), "proxy_ok": proxy_ok,
        "clean_ncand": st.median(clean_ncand) if clean_ncand else 0.0,
        "runs": runs, "lost_n": lost_n, "has_auto": has_auto,
        "reacq": sum(1 for v in state if v == "reacq"),
    }


KINDS = ("absent", "drifted_away", "rejected", "unexplained", "proxy_unusable")


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    main_s, held_s = build_samples()
    by_clip = {c: (b, a) for c, b, a, _ in main_s + held_s}
    K = calibrate()
    print(f"과녁 {len(TARGET7)}건 (7회차 커버 <50% — 사전 등록에 박아 둔 목록)")
    print(f"→ K = {K}   (3~7회차와 같은 규칙·같은 보정용 7건)")
    print("🔴 이 회차는 **읽기만** 한다 — 궤적은 6회차 `track_gate` 그대로다.")

    rows, self_fail = [], []
    for clip in TARGET7:
        if clip not in by_clip:
            print(f"  ⚠ {clip}: 표본에 없다")
            continue
        box, at_ms = by_clip[clip]
        r = run_clip(clip, box, at_ms, K)
        if r is None:
            continue
        if not r["self_ok"]:
            self_fail.append(clip)
        rows.append(r)

    print("\n" + "═" * 104)
    print("🔴 대조군 먼저 — 같은 클립이 **잘 될 때** 얼마나 닮는가")
    print("═" * 104)
    print(f"  {'clip':16s} │ {'깨끗 app':>9s} {'깨끗 프레임':>10s} │ "
          f"{'잃음':>6s} {'재획득':>6s} │ {'후보수(깨끗)':>12s} │ 관문")
    for r in rows:
        gate = "✅ 통과" if r["proxy_ok"] else f"🔴 막힘 (< {TAU})"
        print(f"  {r['clip']:16s} │ {r['clean_med']:9.2f} {r['clean_n']:10d} │ "
              f"{r['lost_n']:6d} {r['reacq']:6d} │ {r['clean_ncand']:12.1f} │ {gate}")
    blocked = [r["clip"] for r in rows if not r["proxy_ok"]]
    print(f"\n  🔴 관문에 막힌 클립 {len(blocked)}/{len(rows)}"
          + (f": {', '.join(blocked)}" if blocked else ""))
    print("     막힌 클립은 **잘 따라갈 때도 안 닮는다** — 「안 닮았다」가 대상 여부를")
    print("     안 말하므로 `rejected` 로 읽지 않는다 (사전 등록 「대조군 관문」).")

    print("\n" + "═" * 104)
    print("구간 분류 — 잃은 프레임 가중")
    print("═" * 104)
    print(f"  {'clip':16s} │ {'구간':>4s} {'잃음':>6s} │ "
          + " ".join(f"{k:>14s}" for k in KINDS))
    total = dict.fromkeys(KINDS, 0)
    for r in rows:
        share = dict.fromkeys(KINDS, 0)
        for run in r["runs"]:
            share[run["kind"]] += run["len"]
            total[run["kind"]] += run["len"]
        print(f"  {r['clip']:16s} │ {len(r['runs']):4d} {r['lost_n']:6d} │ "
              + " ".join(f"{share[k]:14d}" for k in KINDS))
    lost_all = sum(total.values())
    print(f"  {'합계':16s} │ {'':4s} {lost_all:6d} │ "
          + " ".join(f"{total[k]:14d}" for k in KINDS))
    print(f"  {'비율':16s} │ {'':4s} {'':6s} │ "
          + " ".join(f"{total[k] / lost_all:13.0%} " if lost_all else " " * 15
                     for k in KINDS))

    print("\n" + "═" * 104)
    print("자기 검사")
    print("═" * 104)
    print("  A 궤적이 6회차 `track_gate` 와 비트 동일 …… "
          + ("✅ 전수 동일" if not self_fail else "🔴 다르다: " + ", ".join(self_fail)))
    covered = lost_all == sum(r["lost_n"] for r in rows)
    print(f"  B 분류가 잃은 프레임을 빠짐없이 덮는다 …… "
          + ("✅ 만족" if covered else "🔴 불만족"))
    auto_share = (sum(r["has_auto"] for r in rows)
                  / sum(r["lost_n"] for r in rows)) if rows else 0.0
    print(f"  C 잃은 프레임 중 `auto[t]` 있는 비율 ……… {auto_share:.0%}"
          "   (7회차 93% 재현 — 표본·궤적이 같다는 증거)")

    print("\n" + "═" * 104)
    print("사전 등록 결론 (커밋 `60d2673` — 결과를 보고 바꾸지 않았다)")
    print("═" * 104)
    absent_share = (total["absent"] + total["drifted_away"]) / lost_all if lost_all else 0
    rejected_share = total["rejected"] / lost_all if lost_all else 0
    n_proxy = len(blocked)
    print(f"  (가) 대상이 없다  — absent + drifted_away = {absent_share:.0%}"
          f"  (기준 {DOMINANT:.0%})")
    print(f"  (나) 못 알아본다  — rejected            = {rejected_share:.0%}"
          f"  (기준 {DOMINANT:.0%})")
    print(f"  (다) 판별불가     — proxy_unusable 클립 = {n_proxy}건"
          f"  (기준 {PROXY_FAIL}건+)")
    if n_proxy >= PROXY_FAIL:
        verdict = ("**(다) 판별불가.** 과녁의 절반 이상이 대조군 관문에 막혔다 — "
                   "이 방법으로는 못 갈랐다.")
    elif absent_share >= DOMINANT:
        verdict = ("**(가) 대상이 없다.** 🔴 커버리지 붕괴는 결함이 아니다 — "
                   "`None` 이 정직한 답이고 3~7회차 처방 경로를 닫는다.")
    elif rejected_share >= DOMINANT:
        verdict = ("**(나) 있는데 못 알아본다.** 뿌리는 외양 기술자이고 "
                   "3회차의 표류 진단으로 되돌아간다.")
    else:
        verdict = ("**(다) 판별불가.** 한 갈래로 안 몰렸다 — **섞여 있다.** "
                   "섞여 있으면 단일 처방이 안 된다는 것 자체가 결과다.")
    print(f"\n  판정: {verdict}")

    print("\n" + "═" * 104)
    print("함께 보고할 것 (판정에 쓰지 않는다 — 사전 등록 마지막 절)")
    print("═" * 104)
    far = [(run["t_from_anchor"], run["app_lost"])
           for r in rows for run in r["runs"]]
    if far:
        near = [a for d, a in far if d <= st.median([d for d, _ in far])]
        away = [a for d, a in far if d > st.median([d for d, _ in far])]
        print(f"  1) 닻에서 가까운 구간 app 중앙 {st.median(near):.2f}"
              f" · 먼 구간 {st.median(away) if away else float('nan'):.2f}")
        print("     표류면 거리에 따라 완만히 떨어지고, 가림·이탈이면 끊긴다.")
    lens = [run["len"] for r in rows for run in r["runs"]]
    if lens:
        print(f"  2) 구간 길이 — 중앙 {st.median(lens):.0f}프레임 · "
              f"최장 {max(lens)} · 구간 {len(lens)}개")
    print(f"  3) 재획득이 뒤에 일어난 클립 "
          f"{sum(1 for r in rows if r['reacq'] > 0)}/{len(rows)}"
          " — 일어났으면 **대상이 돌아왔다**는 뜻이라 (가)에 무게")
    print(f"  4) 후보 수 — 깨끗 중앙 "
          f"{st.median([r['clean_ncand'] for r in rows]):.1f} · "
          f"잃음 중앙 "
          f"{st.median([run['n_cand'] for r in rows for run in r['runs']]):.1f}")


if __name__ == "__main__":
    main()
