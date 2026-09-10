#!/usr/bin/env python3
"""**돌아온 상자가 잃기 직전 상자와 이어지는가** (미결 18번 10회차).

    uv run python eval/pending18_link/measure_link.py    # GPU 불필요

9회차 판정은 **(가) 닻도 못 알아본다 96%** 였고, 그 문장이 둘을 안 가른다 —
**(i) 후보가 진짜 남이다**(→ `None` 이 정직한 답) 와 **(ii) 대상인데 그동안
안 닮아 보인다**(→ 뿌리는 닻 기술자). 재획득은 **닻 기준**으로 고른 것이라
트래커 자신이 낸 「이것이 대상이다」 선언이다. 그 상자를 **잃기 직전 상자**와
공간으로 이어 본다.

🔴 **여기도 IoU 라 8회차처럼 길이에 오염될 수 있다.** 구간이 길면 사람이
실제로 이동하므로 이어져도 안 겹친다. 그래서 **짧은 구간만 주 층**으로 쓰고
(사다리 10→20→30 을 사전 등록에 고정), 주 층 안에서 길이 상관을 다시 잰다.

규격은 `PREREGISTRATION.md`(커밋 `3f4a415`, 코드보다 먼저).

🔴 **`src/` 와 앞 회차 스크립트를 고치지 않는다. 「같은 사람인가」의 문턱은
production `MIN_ANCHOR_IOU` 그대로라 이 회차가 만든 자유도는 0 이다.**
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
            "eval/pending18_presence", "eval/pending18_drift"):
    sys.path.insert(0, str(ROOT / sub))

from measure_appearance import BOXES, boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_conservative import (  # noqa: E402
    ALPHA, REACQ_K, REACQ_TAU, TAU, UPDATE_TAU, calibrate,
)
from measure_coverage import TARGET7, build_samples  # noqa: E402
from measure_drift import MIN_CLEAN, spearman  # noqa: E402
from measure_gate import GATE_TAU, track_gate  # noqa: E402
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import RESCUE_IOU, low_from_cache  # noqa: E402
from supersub_agent.pose import SubjectRequest, _iou, read_frames  # noqa: E402

# --- 사전 등록: 새 상수는 「표본 크기」에 관한 둘뿐이다 ---------------------
LINK_IOU = RESCUE_IOU     # = MIN_ANCHOR_IOU = 0.3. production 의 「같은 사람인가」
SHORT_CAPS = (10, 20, 30)  # 이 순서로 처음 MIN_RUNS 를 채우는 상한이 주 층
MIN_RUNS = 8              # 주 층에 필요한 최소 구간 수
MIN_CLIPS = 3             # 주 층 구간이 나와야 하는 최소 클립 수
DOMINANT = 0.70           # 결론 임계 — 8·9회차와 같은 폭
RHO_BAR = 0.50            # 기준 D — 주 층 안에서 길이와의 상관 상한
EXTRA = "O2GSaYqH8JY"     # 층 C
SENS = (0.1, 0.2, 0.3, 0.5)   # 문턱 민감도 (판정은 LINK_IOU 에서만)


def track_linked(auto, cands, lows, frames, subject, fps, wh, K):
    """6회차 `track_gate` **그대로** + 잃기/재획득 두 점의 기록.

    🔴 판단 흐름을 한 줄도 안 바꿨다. 더한 것은 `links`·`state` 기록뿐이고,
    main 이 `chosen` 을 `track_gate` 와 비교해 그것을 확인한다(기준 A).

    반환: (chosen, state, links, orphans)
      links[i]  = {t_loss, t_reacq, prev_box, reacq_box, run_len}
      orphans   = 재획득으로 끝나지 못한 구간의 길이 목록
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, [None] * n, [], []

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    state: list[str | None] = [None] * n
    links: list[dict] = []
    orphans: list[int] = []
    chosen[anchor] = seed
    state[anchor] = "anchor"

    def app(ref, t, box):
        if ref is None or box is None or t >= len(frames):
            return 1.0
        return similarity(ref, hist_of(frames[t], box))

    def walk(order, start):
        previous, ref, lost, bad, good = start, ah, False, 0, 0
        pending: dict | None = None      # 🔴 기록용. 판단에 안 쓴다
        last = None
        for t in order:
            last = t
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
                        # 잃는 순간 — `previous` 는 구간 동안 갱신되지 않는다
                        pending = {"t_loss": t, "prev_box": previous}
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
                if pending is not None:
                    # 🔴 이 회차가 여는 자리 — 두 점을 잇는다
                    pending.update({"t_reacq": t, "reacq_box": best,
                                    "run_len": abs(t - pending["t_loss"]),
                                    "reacq_app": best_app})
                    links.append(pending)
                    pending = None
            else:
                chosen[t] = None
                state[t] = "lost"
        if pending is not None and last is not None:
            orphans.append(abs(last - pending["t_loss"]) + 1)

    walk(range(anchor + 1, n), seed)
    walk(range(anchor - 1, -1, -1), seed)
    return chosen, state, links, orphans


def centre(b):
    x, y, w, h = b
    return (x + w / 2.0, y + h / 2.0)


def run_clip(clip, box, at_ms, K):
    auto, cands, wh, fps = boxes_from_cache(clip)
    lows, _f = low_from_cache(clip)
    frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
    subject = SubjectRequest(box=box, at_ms=at_ms)
    anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return None

    g6, _rq, _ev, _bl = track_gate(auto, cands, lows, frames, subject, fps, wh, K)
    chosen, state, links, orphans = track_linked(auto, cands, lows, frames,
                                                 subject, fps, wh, K)
    same = list(chosen) == list(g6)

    def app_at(t, b):
        if b is None or t >= len(frames):
            return 0.0
        h = hist_of(frames[t], b)
        return similarity(ah, h) if h is not None else 0.0

    # 대조군 — 9회차 관문 그대로 (닻은 뺀다)
    clean = [app_at(t, chosen[t]) for t, v in enumerate(state)
             if v in ("pick", "reacq")]

    for lk in links:
        p, r = lk["prev_box"], lk["reacq_box"]
        lk["clip"] = clip
        lk["link_iou"] = _iou(p, r)
        # 보조 1 — 재획득 프레임의 후보 중 prev 에 가장 가까운 것이 그것인가
        near, near_iou = None, -1.0
        for cand in cands[lk["t_reacq"]]:
            iou = _iou(p, cand)
            if iou > near_iou:
                near, near_iou = cand, iou
        lk["n_cand"] = len(cands[lk["t_reacq"]])
        lk["nearest"] = near is not None and tuple(near) == tuple(r)
        lk["near_iou"] = max(near_iou, 0.0)
        # 보조 2 — 프레임당 몇 상자폭 움직였나
        (px, py), (rx, ry) = centre(p), centre(r)
        w = (p[2] + r[2]) / 2.0
        d = ((px - rx) ** 2 + (py - ry) ** 2) ** 0.5
        lk["reach"] = d / (w * lk["run_len"]) if w and lk["run_len"] else 0.0

    return {
        "clip": clip, "self_ok": same,
        "clean_med": st.median(clean) if clean else 0.0,
        "clean_n": len(clean),
        "links": links, "orphans": orphans,
    }


def gate(r):
    """대조군 관문 — 9회차 그대로."""
    return r["clean_n"] >= MIN_CLEAN and r["clean_med"] >= TAU


def share_linked(links, bar=LINK_IOU):
    if not links:
        return 0.0, 0
    n = sum(1 for lk in links if lk["link_iou"] >= bar)
    return n / len(links), n


def summarize(rows, title):
    print("\n" + "═" * 100)
    print(title)
    print("═" * 100)
    print(f"  {'clip':16s} │ {'깨끗n':>6s} {'깨끗app':>7s} {'관문':>5s} │ "
          f"{'재획득':>6s} {'미완':>4s} │ {'짧은구간':>8s} {'이어짐':>6s}")
    for r in sorted(rows, key=lambda x: x["clip"]):
        ok = gate(r)
        short = [lk for lk in r["links"] if lk["run_len"] <= SHORT_CAPS[0]]
        _f, n = share_linked(short)
        print(f"  {r['clip']:16s} │ {r['clean_n']:6d} {r['clean_med']:7.2f} "
              f"{'✅' if ok else '🔴':>5s} │ {len(r['links']):6d} "
              f"{len(r['orphans']):4d} │ {len(short):8d} {n:6d}")
    return [r for r in rows if gate(r)]


def ladder(kept_links):
    """사전 등록한 사다리 — 처음으로 MIN_RUNS 를 채우는 상한이 주 층."""
    for cap in SHORT_CAPS:
        sel = [lk for lk in kept_links if lk["run_len"] <= cap]
        if len(sel) >= MIN_RUNS:
            return cap, sel
    return None, [lk for lk in kept_links if lk["run_len"] <= SHORT_CAPS[-1]]


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    main_s, held_s = build_samples()
    K = calibrate()
    pool = {c: (b, a) for c, b, a, _ in main_s + held_s}
    print(f"→ K = {K}   (3~9회차와 같은 규칙·같은 보정용 7건)")
    print("🔴 읽기만 한다 — 궤적은 6회차 `track_gate` 그대로다.")
    print(f"🔴 「같은 사람인가」 문턱은 production 그대로 LINK_IOU = {LINK_IOU}. "
          "이 회차의 새 상수는 표본 크기 둘뿐이다.")
    print("🔴 이번엔 「안 쓴 표본」이 없다 — 9회차가 층 B·C 를 다 썼다 (사전 등록).")

    layers, self_fail = {}, []
    for name, clips in (
        ("A", [c for c in TARGET7 if c in pool]),
        ("B", [c for c in pool if c not in TARGET7]),
        ("C", [EXTRA] if EXTRA in BOXES else []),
    ):
        rows = []
        for clip in clips:
            box, at_ms = (BOXES[clip] if name == "C" else pool[clip])
            r = run_clip(clip, box, at_ms, K)
            if r is None:
                continue
            if not r["self_ok"]:
                self_fail.append(clip)
            rows.append(r)
        layers[name] = rows

    kA = summarize(layers["A"], "층 A — 과녁 7건 (커버리지 붕괴로 골라낸 것)")
    kB = summarize(layers["B"], "층 B — 과녁 밖 (안 무너진 클립)")
    kC = summarize(layers["C"], f"층 C — {EXTRA}")

    kept = {"A": kA, "B": kB, "C": kC}
    all_links = [lk for n in ("A", "B", "C") for r in kept[n] for lk in r["links"]]
    cap, primary = ladder(all_links)

    # --- 주 층 --------------------------------------------------------------
    print("\n" + "═" * 100)
    print("🔴 주 층 — 사다리로 정한 상한 (표본 수로만 정한다. 사전 등록)")
    print("═" * 100)
    for c in SHORT_CAPS:
        sel = [lk for lk in all_links if lk["run_len"] <= c]
        f, n = share_linked(sel)
        mark = "  ← 주 층" if c == cap else ""
        print(f"  ≤{c:3d}프레임 … 구간 {len(sel):3d} · 이어짐 {n:3d} "
              f"({f:.0%}){mark}")
    f_all, n_all = share_linked(all_links)
    print(f"  제한 없음 … 구간 {len(all_links):3d} · 이어짐 {n_all:3d} ({f_all:.0%})"
          "   ← 🔴 판정에 안 쓴다 (길이 오염)")
    if cap is None:
        print(f"\n  🔴 사다리를 다 내려가도 {MIN_RUNS}구간을 못 채웠다 — 기준 B 불합격")

    print(f"\n  {'clip':16s} {'잃음t':>6s} {'재획득t':>7s} {'길이':>4s} "
          f"{'link_iou':>9s} {'이어짐':>6s} {'가장가까움':>10s} {'reach':>7s} "
          f"{'후보':>4s}")
    for lk in sorted(primary, key=lambda x: (x["clip"], x["t_loss"])):
        print(f"  {lk['clip']:16s} {lk['t_loss']:6d} {lk['t_reacq']:7d} "
              f"{lk['run_len']:4d} {lk['link_iou']:9.2f} "
              f"{'✅' if lk['link_iou'] >= LINK_IOU else '🔴':>6s} "
              f"{'✅' if lk['nearest'] else '🔴':>10s} {lk['reach']:7.2f} "
              f"{lk['n_cand']:4d}")

    # --- 기준 D: 계기 검사 ---------------------------------------------------
    print("\n" + "═" * 100)
    print("🔴 기준 D — 계기 검사: 주 지표가 길이에 물들었는가")
    print("═" * 100)
    if len(primary) >= 3:
        rho_in = spearman([lk["run_len"] for lk in primary],
                          [lk["link_iou"] for lk in primary])
        print(f"  주 층 안에서   link_iou 대 구간 길이  ρ = {rho_in:+.2f}"
              + ("   🔴 기준 D 위반" if abs(rho_in) >= RHO_BAR else ""))
        d_ok = abs(rho_in) < RHO_BAR
    else:
        print("  주 층 구간이 3개 미만이라 상관을 못 낸다")
        rho_in, d_ok = float("nan"), False
    if len(all_links) >= 3:
        rho_all = spearman([lk["run_len"] for lk in all_links],
                           [lk["link_iou"] for lk in all_links])
        print(f"  전 구간에서    link_iou 대 구간 길이  ρ = {rho_all:+.2f}"
              "   (참고 — 층화가 왜 필요했는지가 여기 보인다)")

    # --- 판정 ---------------------------------------------------------------
    print("\n" + "═" * 100)
    print("사전 등록 판정 (커밋 `3f4a415` — 결과를 보고 바꾸지 않았다)")
    print("═" * 100)
    a_ok = not self_fail
    print("  A 궤적 비트 동일 …………………………… "
          + ("✅ 전수 동일" if a_ok else "🔴 " + ", ".join(self_fail)))
    n_clips = len({lk["clip"] for lk in primary})
    b_ok = cap is not None and len(primary) >= MIN_RUNS and n_clips >= MIN_CLIPS
    print(f"  B 주 층 {MIN_RUNS}구간+ · {MIN_CLIPS}클립+ ………… "
          f"{'✅' if b_ok else '🔴'} (상한 {cap} · {len(primary)}구간 · {n_clips}클립)")

    by_layer = {}
    pri_ids = {id(lk) for lk in primary}
    for name in ("A", "B", "C"):
        sel = [lk for r in kept[name] for lk in r["links"] if id(lk) in pri_ids]
        if len(sel) >= 3:
            f, _n = share_linked(sel)
            by_layer[name] = f
    sides = {n: ("이어짐" if f >= 0.5 else "안이어짐") for n, f in by_layer.items()}
    c_ok = len(by_layer) >= 2 and len(set(sides.values())) == 1
    detail = " · ".join(f"{n}={sides[n]} {by_layer[n]:.0%}" for n in sorted(by_layer))
    print(f"  C 층 일치 (3구간+ 인 층끼리) ……… "
          f"{'✅' if c_ok else '🔴'} ({detail if by_layer else '3구간+ 인 층이 없다'})")
    print(f"  D 계기 검사 (|ρ| < {RHO_BAR}) ……………… {'✅ 만족' if d_ok else '🔴 위반'}")
    f_pri, n_pri = share_linked(primary)
    e_ok = f_pri >= DOMINANT or (1 - f_pri) >= DOMINANT
    print(f"  E 다수 쪽 {DOMINANT:.0%}+ ………………………… "
          f"{'✅' if e_ok else '🔴'} (이어짐 {f_pri:.0%} · 안이어짐 {1 - f_pri:.0%})")

    if not (a_ok and b_ok and d_ok):
        verdict = ("**(다) 판별불가.** 기준 A·B·D 중 하나가 안 섰다 — "
                   "숫자를 결론으로 쓰지 않는다.")
    elif not c_ok:
        verdict = ("**(다) 판별불가.** 층이 **갈렸다**(또는 확인할 층이 부족하다) — "
                   "붕괴로 고른 표본과 안 고른 표본에서 답이 다르다.")
    elif not e_ok:
        verdict = ("**(다) 판별불가 — 🔴 섞여 있다.** 두 사정이 함께 일어난다는 "
                   "뜻이고, 처방을 하나로 못 고른다는 것이 이 회차의 답이다.")
    elif f_pri >= DOMINANT:
        verdict = ("**(ii) 대상은 거기 있었다.** 돌아온 자리가 잃은 자리다 — "
                   "뿌리는 **닻 기술자**(색 히스토그램)이고, 다음은 더 강한 "
                   "외양 표현이다.")
    else:
        verdict = ("**(i) 대상이 없었다.** 딴 데서 돌아온다 — 구간의 상자는 "
                   "남이고 **`None` 이 정직한 답이다.** 커버리지 붕괴는 결함이 "
                   "아니다.")
    print(f"\n  판정: {verdict}")
    print(f"        주 층 {len(primary)}구간 — 이어짐 {n_pri} · "
          f"안이어짐 {len(primary) - n_pri}")

    # --- 함께 보고 -----------------------------------------------------------
    print("\n" + "═" * 100)
    print("함께 보고할 것 (판정에 쓰지 않는다)")
    print("═" * 100)
    print("  1) 문턱 민감도 (주 층) — 판정은 "
          f"{LINK_IOU} 에서만 한다")
    for bar in SENS:
        f, n = share_linked(primary, bar)
        print(f"       IoU ≥ {bar:.1f} … 이어짐 {n}/{len(primary)} ({f:.0%})")
    if primary:
        near = sum(1 for lk in primary if lk["nearest"])
        one = sum(1 for lk in primary if lk["n_cand"] <= 1)
        print(f"  2) `nearest` — 재획득 상자가 prev 에 가장 가까운 후보 "
              f"{near}/{len(primary)} ({near / len(primary):.0%}) "
              f"· 후보가 1개뿐이라 자명한 것 {one}건")
        print(f"  3) `reach` — 프레임당 상자폭 이동 중앙 "
              f"{st.median([lk['reach'] for lk in primary]):.2f} "
              f"· 최대 {max(lk['reach'] for lk in primary):.2f}")
        print(f"  4) 재획득 시 닻 유사도 중앙 "
              f"{st.median([lk['reacq_app'] for lk in primary]):.2f} "
              f"(문턱 {REACQ_TAU})")
    blocked = [r for n in ("A", "B", "C") for r in layers[n] if not gate(r)]
    bl = [lk for r in blocked for lk in r["links"] if lk["run_len"] <= (cap or SHORT_CAPS[-1])]
    if bl:
        f, n = share_linked(bl)
        print(f"  5) 관문에 막힌 클립 {len(blocked)}건의 같은 값 — "
              f"이어짐 {n}/{len(bl)} ({f:.0%}) · 🔴 판정에 안 쓴다")
    orph = [x for n in ("A", "B", "C") for r in kept[n] for x in r["orphans"]]
    if orph:
        print(f"  6) 재획득으로 **안 끝난** 구간 {len(orph)}건 · 길이 중앙 "
              f"{st.median(orph):.0f} — 🔴 이 회차가 못 보는 부분이다")


if __name__ == "__main__":
    main()
