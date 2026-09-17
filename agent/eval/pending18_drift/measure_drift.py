#!/usr/bin/env python3
"""**거부를 일으킨 것이 표류인가** (미결 18번 9회차).

    uv run python eval/pending18_drift/measure_drift.py    # GPU 불필요

거부는 한 줄에서 일어난다 — `app(ref, pick) < TAU`. `ref` 는 갱신되며
흘러가고 `ah`(닻)는 고정이다. **그 프레임에서 둘을 나란히 보면 원인이
바로 나온다.**

🔴 **8회차 결함의 해독제다.** 거부는 **한 프레임의 사건**이라 구간 길이가
값에 안 들어온다. 8회차의 `cont_iou` 는 구간 내내 고정된 `previous` 와의
IoU라 길이가 분류를 정했다(≤10프레임 0.76 대 >40프레임 0.07).

🔴 **8회차의 사후 값(27/73)을 쓰지 않는다.** 그 값을 보고 세운 기준은 같은
표본에서 순환이라, 이 회차는 **다른 양**을 묻는다.

규격은 `PREREGISTRATION.md`(커밋 `95856f7`, 코드보다 먼저).

🔴 **`src/` 와 앞 회차 스크립트를 고치지 않는다. 새 상수는 `MIN_CLEAN` 하나다.**
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

from measure_appearance import BOXES, boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_conservative import (  # noqa: E402
    ALPHA, REACQ_K, REACQ_TAU, TAU, UPDATE_TAU, calibrate,
)
from measure_coverage import TARGET7, build_samples  # noqa: E402
from measure_gate import GATE_TAU, track_gate  # noqa: E402
from measure_reacquire import CLIPS, anchor_of  # noqa: E402
from measure_rescue import RESCUE_IOU, low_from_cache, synthetic_anchor  # noqa: E402
from supersub_agent.pose import SubjectRequest, _iou, read_frames  # noqa: E402

# --- 사전 등록: 이 회차의 새 상수는 하나다 --------------------------------
MIN_CLEAN = 20     # 대조군 관문의 최소 깨끗 장수 (닻 제외)
DOMINANT = 0.70    # 결론 임계 — 8회차와 같은 폭
RHO_BAR = 0.50     # 기준 D — 길이와의 상관이 이만큼이면 판정 무효
MIN_CLIPS = 3      # 기준 B — 층마다 남아야 하는 클립 수
EXTRA = "O2GSaYqH8JY"   # 층 C — 풀에서 한 번도 안 쓴 유일한 클립


def track_reasoned(auto, cands, lows, frames, subject, fps, wh, K):
    """6회차 `track_gate` **그대로** + 거부 시점의 두 의견을 기록.

    🔴 판단 흐름을 한 줄도 안 바꿨다. 더한 것은 `rejects`·`state` 기록뿐이고,
    main 이 `chosen` 을 `track_gate` 와 비교해 그것을 확인한다.

    반환: (chosen, state, rejects)
      rejects[i] = {t, ref_app, anchor_app, since_anchor}
    """
    n = len(auto)
    anchor, seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return auto, [None] * n, []

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    state: list[str | None] = [None] * n
    rejects: list[dict] = []
    chosen[anchor] = seed
    state[anchor] = "anchor"

    def app(ref, t, box):
        if ref is None or box is None or t >= len(frames):
            return 1.0
        return similarity(ref, hist_of(frames[t], box))

    def walk(order, start):
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
                        # 🔴 여기가 이 회차가 여는 자리 — 거부의 두 의견.
                        #    `ref` 는 흘러간 값, `ah` 는 고정된 닻이다.
                        rejects.append({
                            "t": t, "ref_app": a, "anchor_app": app(ah, t, pick),
                            "since_anchor": abs(t - anchor),
                        })
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
    return chosen, state, rejects


def runs_of(state, kind="lost"):
    out, s = [], None
    for t, v in enumerate(state):
        if v == kind:
            if s is None:
                s = t
        elif s is not None:
            out.append((s, t - 1))
            s = None
    if s is not None:
        out.append((s, len(state) - 1))
    return out


def spearman(xs, ys):
    """순위 상관. 표본이 작아 정규성을 가정하지 않는다."""
    n = len(xs)
    if n < 3:
        return float("nan")

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


def run_clip(clip, box, at_ms, K):
    auto, cands, wh, fps = boxes_from_cache(clip)
    lows, _f = low_from_cache(clip)
    frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
    subject = SubjectRequest(box=box, at_ms=at_ms)
    anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
    if anchor is None:
        return None

    g6, _rq, _ev, _bl = track_gate(auto, cands, lows, frames, subject, fps, wh, K)
    chosen, state, rejects = track_reasoned(auto, cands, lows, frames,
                                            subject, fps, wh, K)
    same = list(chosen) == list(g6)

    def app_at(t, b):
        if b is None or t >= len(frames):
            return 0.0
        h = hist_of(frames[t], b)
        return similarity(ah, h) if h is not None else 0.0

    clean_t = [t for t, v in enumerate(state)
               if v in ("pick", "reacq") ]          # 🔴 닻은 뺀다 (8회차 교훈)
    clean = [app_at(t, chosen[t]) for t in clean_t]

    lost = runs_of(state)
    # 구간마다: 길이 · 재획득으로 끝났는가 · 구간 내 닻 최선의 중앙값
    per_run = []
    for s, e in lost:
        best = []
        for t in range(s, e + 1):
            best.append(max((app_at(t, c) for c in cands[t]), default=0.0))
        per_run.append({
            "run": (s, e), "len": e - s + 1,
            "anchor_best": st.median(best) if best else 0.0,
            "reacq_linked": e + 1 < len(state) and state[e + 1] == "reacq"
            or (s - 1 >= 0 and state[s - 1] == "reacq"),
        })
    # 거부 사건과 그 뒤 구간을 잇는다 (거부 프레임이 구간의 첫 프레임이다)
    by_start = {r["run"][0]: r for r in per_run}
    for rj in rejects:
        r = by_start.get(rj["t"])
        rj["run_len"] = r["len"] if r else 1
        rj["n_cand"] = len(cands[rj["t"]])

    return {
        "clip": clip, "self_ok": same,
        "clean_med": st.median(clean) if clean else 0.0,
        "clean_n": len(clean),
        "rejects": rejects, "runs": per_run,
        "lost_n": sum(r["len"] for r in per_run),
    }


def gate(r):
    """대조군 관문 — 사전 등록 기준 B."""
    return r["clean_n"] >= MIN_CLEAN and r["clean_med"] >= TAU


def summarize(rows, title):
    print("\n" + "═" * 100)
    print(title)
    print("═" * 100)
    print(f"  {'clip':16s} │ {'깨끗n':>6s} {'깨끗app':>7s} {'관문':>5s} │ "
          f"{'거부':>4s} │ {'표류':>4s} {'닻도모름':>8s} │ {'잃음':>6s}")
    drift = blind = 0
    for r in sorted(rows, key=lambda x: x["clip"]):
        ok = gate(r)
        d = sum(1 for j in r["rejects"]
                if j["ref_app"] < TAU <= j["anchor_app"])
        b = sum(1 for j in r["rejects"] if j["anchor_app"] < TAU)
        if ok:
            drift += d
            blind += b
        print(f"  {r['clip']:16s} │ {r['clean_n']:6d} {r['clean_med']:7.2f} "
              f"{'✅' if ok else '🔴':>5s} │ {len(r['rejects']):4d} │ "
              f"{d:4d} {b:8d} │ {r['lost_n']:6d}")
    kept = [r for r in rows if gate(r)]
    tot = drift + blind
    print(f"\n  관문 통과 {len(kept)}/{len(rows)}건 · 거부 사건 {tot}건 "
          f"(관문 통과 클립만)")
    if tot:
        print(f"  🔴 **표류** (ref 는 거부, 닻은 알아봄) … {drift}/{tot} = {drift / tot:.0%}")
        print(f"     닻도 못 알아봄 ………………………… {blind}/{tot} = {blind / tot:.0%}")
    return kept, drift, blind


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    main_s, held_s = build_samples()
    K = calibrate()
    pool = {c: (b, a) for c, b, a, _ in main_s + held_s}
    print(f"→ K = {K}   (3~8회차와 같은 규칙·같은 보정용 7건)")
    print("🔴 읽기만 한다 — 궤적은 6회차 `track_gate` 그대로다.")
    print(f"🔴 새 상수는 MIN_CLEAN = {MIN_CLEAN} 하나다 (사전 등록).")

    layers, self_fail = {}, []
    for name, clips in (
        ("A", [c for c in TARGET7 if c in pool]),
        ("B", [c for c in pool if c not in TARGET7]),
    ):
        rows = []
        for clip in clips:
            box, at_ms = pool[clip]
            r = run_clip(clip, box, at_ms, K)
            if r is None:
                continue
            if not r["self_ok"]:
                self_fail.append(clip)
            if r["rejects"] or name == "A":
                rows.append(r)
        layers[name] = rows

    # 층 C — 풀 밖의 유일한 미사용 클립
    c_rows = []
    if EXTRA in BOXES:
        box, at_ms = BOXES[EXTRA]
        r = run_clip(EXTRA, box, at_ms, K)
        if r is not None:
            c_rows.append(r)
            if not r["self_ok"]:
                self_fail.append(EXTRA)
    layers["C"] = c_rows

    kA, dA, bA = summarize(layers["A"], "층 A — 과녁 7건 (🔴 8회차에 썼다)")
    kB, dB, bB = summarize(layers["B"], "층 B — 과녁 밖 (✅ 이 질문에 처음 쓴다)")
    kC, dC, bC = summarize(layers["C"], f"층 C — {EXTRA} (✅ 풀에서 한 번도 안 썼다)")

    # --- 기준 D: 계기 검사 -------------------------------------------------
    allj = [j for name in ("A", "B", "C") for r in layers[name]
            if gate(r) for j in r["rejects"]]
    print("\n" + "═" * 100)
    print("🔴 기준 D — 계기 검사: 주 지표가 무엇에 반응하는가")
    print("═" * 100)
    if len(allj) >= 3:
        for lab, key in (("구간 길이", "run_len"), ("후보 수", "n_cand"),
                         ("닻에서의 거리", "since_anchor")):
            rho = spearman([j[key] for j in allj], [j["anchor_app"] for j in allj])
            mark = ("🔴 기준 D 위반" if lab == "구간 길이" and abs(rho) >= RHO_BAR
                    else "")
            print(f"  anchor_app 대 {lab:12s} Spearman ρ = {rho:+.2f}  {mark}")
        d_ok = abs(spearman([j["run_len"] for j in allj],
                            [j["anchor_app"] for j in allj])) < RHO_BAR
    else:
        print("  거부 사건이 3건 미만이라 상관을 못 낸다")
        d_ok = False
    print("  → 8회차의 `cont_iou` 는 길이와 강하게 얽혀 있었다."
          " 여기 값이 작아야 계기가 산다.")

    # --- 판정 -------------------------------------------------------------
    print("\n" + "═" * 100)
    print("사전 등록 판정 (커밋 `95856f7` — 결과를 보고 바꾸지 않았다)")
    print("═" * 100)
    a_ok = not self_fail
    print(f"  A 궤적 비트 동일 …………………………… "
          + ("✅ 전수 동일" if a_ok else "🔴 " + ", ".join(self_fail)))
    b_ok = len(kA) >= MIN_CLIPS and len(kB) >= MIN_CLIPS
    print(f"  B 관문 통과 클립 층마다 {MIN_CLIPS}건+ …… "
          f"{'✅' if b_ok else '🔴'} 만족 (A {len(kA)}건 · B {len(kB)}건 · C {len(kC)}건)")

    def side(d, b):
        t = d + b
        return (d / t if t else 0.0), (b / t if t else 0.0)
    dfA, bfA = side(dA, bA)
    dfB, bfB = side(dB, bB)
    winA = "표류" if dfA > bfA else "닻도모름"
    winB = "표류" if dfB > bfB else "닻도모름"
    c_ok = winA == winB and (dA + bA) > 0 and (dB + bB) > 0
    print(f"  C 층 A·B 다수 쪽 일치 ………………… "
          f"{'✅' if c_ok else '🔴'} (A={winA} {max(dfA, bfA):.0%} · "
          f"B={winB} {max(dfB, bfB):.0%})")
    print(f"  D 계기 검사 (|ρ| < {RHO_BAR}) ……………… {'✅ 만족' if d_ok else '🔴 위반'}")
    d_tot, b_tot = dA + dB + dC, bA + bB + bC
    tot = d_tot + b_tot
    share = max(d_tot, b_tot) / tot if tot else 0.0
    print(f"  E 다수 쪽 {DOMINANT:.0%}+ ………………………… "
          f"{'✅' if share >= DOMINANT else '🔴'} ({share:.0%})")

    if not (a_ok and b_ok and d_ok):
        verdict = ("**(다) 판별불가.** 기준 A·B·D 중 하나가 안 섰다 — "
                   "숫자를 결론으로 쓰지 않는다.")
    elif not c_ok:
        verdict = ("**(다) 판별불가.** 층 A 와 층 B 가 **갈렸다** — "
                   "붕괴로 고른 표본과 안 고른 표본에서 답이 다르다.")
    elif share < DOMINANT:
        verdict = ("**(다) 판별불가.** 한 갈래로 안 몰렸다 — **섞여 있다.**")
    elif d_tot > b_tot:
        verdict = ("**(나) 표류다.** 🔴 닻은 알아보는데 흘러간 `ref` 가 "
                   "거부했다. 뿌리는 `ref` 갱신이고 3회차 진단으로 돌아간다.")
    else:
        verdict = ("**(가) 닻도 못 알아본다.** 표류가 아니다 — "
                   "후보가 남이거나 외양이 진짜로 변했다.")
    print(f"\n  판정: {verdict}")
    print(f"        전체 거부 {tot}건 — 표류 {d_tot} · 닻도모름 {b_tot}")

    # --- 함께 보고 --------------------------------------------------------
    print("\n" + "═" * 100)
    print("함께 보고할 것 (판정에 쓰지 않는다)")
    print("═" * 100)
    linked = [r for name in ("A", "B", "C") for row in layers[name]
              for r in row["runs"]]
    if linked:
        n_link = sum(1 for r in linked if r["reacq_linked"])
        print(f"  1) 재획득으로 이어진 구간 {n_link}/{len(linked)} "
              f"({n_link / len(linked):.0%}) — 트래커 자신이 닻 기준으로 "
              "「대상이다」라고 말한 것이다")
        print(f"  2) 구간 내 닻 최선(`anchor_best`) 중앙 "
              f"{st.median([r['anchor_best'] for r in linked]):.2f} "
              f"— {TAU} 이상이면 구간 **내내** 알아볼 수 있었다는 뜻이다")
    if allj:
        gap = [j["anchor_app"] - j["ref_app"] for j in allj]
        print(f"  3) 표류의 크기 (`anchor_app - ref_app`) — 중앙 "
              f"{st.median(gap):+.2f} · 최대 {max(gap):+.2f} · 최소 {min(gap):+.2f}")
        print(f"  4) 닻에서 거부까지 — 중앙 "
              f"{st.median([j['since_anchor'] for j in allj]):.0f}프레임 "
              f"· 최대 {max(j['since_anchor'] for j in allj)}")


if __name__ == "__main__":
    main()
