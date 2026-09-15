"""사후 관찰 — **주 층이 왜 비었는가**. 🔴 판정에 안 쓴다 (미결 `ho` 18번 11회차).

사전 등록 판정은 이미 났다(분모 0편 → 판별 불가). 이 스크립트는 **문턱을
돌리지 않고** 그 결과가 「현상」인지 「계기 결함」인지 가르는 데만 쓴다.

🔴 **GPU 를 안 쓴다** — 본 회차가 남긴 `proximity_raw.json` 을 읽는다.

    cd agent && uv run python eval/pending18_ball_proximity/posthoc_why_empty.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "pending45_touch_events" / "touches_raw.json"

NEAR = 0.25


def pct(v: list[float], q: float) -> float:
    s = sorted(v)
    if not s:
        return float("nan")
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


def main() -> None:
    clips = [c for c in json.loads((HERE / "proximity_raw.json").read_text("utf-8"))
             if c.get("rows")]
    rows = [r for c in clips for r in c["rows"]]
    print(f"클립 {len(clips)}편 · 공이 보인 프레임 {len(rows)}개\n")

    # ⑴ 「가장 가까운 사람」이 얼마나 가까운가 — 문턱이 아니라 분포를 본다
    dmin = [r["d_min"] for r in rows]
    print("⑴ 최근접 후보의 발치↔공 거리 (키높이 단위)")
    for q in (0.0, 0.05, 0.25, 0.5, 0.75, 1.0):
        print(f"     p{int(q*100):3d} : {pct(dmin, q):.2f}")
    print(f"     ≤{NEAR} 인 프레임 : {sum(d <= NEAR for d in dmin)}/{len(dmin)}")
    for band in (0.5, 0.75, 1.0, 1.5, 2.0):
        print(f"     ≤{band:.2f} 인 프레임 : {sum(d <= band for d in dmin)}/{len(dmin)}"
              f" ({sum(d <= band for d in dmin)/len(dmin):.0%})")

    # ⑵ 후보 수 — 단일후보 오염이 얼마나 되는가
    multi = [r for r in rows if r["n_cands"] >= 2]
    print(f"\n⑵ 후보 2명 이상인 프레임 : {len(multi)}/{len(rows)} "
          f"({len(multi)/len(rows):.0%}) · 후보 수 중앙 "
          f"{statistics.median([r['n_cands'] for r in rows])}")

    # ⑶ 🔴 자(scale)가 현상을 만들었는가 — 후보 자기 키로 다시 재 본다
    #    (판정에 안 쓴다. 사전 등록은 클립 중앙 키로 굳었다.)
    print("\n⑶ 자를 바꿔 보면 — 최근접 후보 **자기 키**로 정규화하면")
    alt = []
    for c in clips:
        H = c["scale_h"]
        for r in c["rows"]:
            if r["h_argmin"] > 0:
                alt.append(r["d_min"] * H / r["h_argmin"])
    print(f"     중앙 {statistics.median(alt):.2f} · "
          f"≤{NEAR} 인 프레임 {sum(d <= NEAR for d in alt)}/{len(alt)}")
    ratios = [r["h_argmin"] / c["scale_h"]
              for c in clips for r in c["rows"] if r["h_argmin"] > 0]
    print(f"     최근접 후보 키 ÷ 클립 중앙 키 : 중앙 {statistics.median(ratios):.2f} "
          f"· p5 {pct(ratios, .05):.2f} · p95 {pct(ratios, .95):.2f}")

    # ⑷ 자와 무관한 질문 — argmin 은 정규화에 의존하지 않는다
    print("\n⑷ 🔴 **자와 무관한** 물음 — 공이 보이고 후보가 2명 이상인 프레임에서")
    if multi:
        m = sum(r["match"] for r in multi) / len(multi)
        miss = [r for r in multi if not r["match"]]
        marg = [r["d_chosen"] - r["d_min"] for r in miss]
        ratio = [r["h_chosen"] / r["h_argmin"] for r in miss if r["h_argmin"] > 0]
        print(f"     우리가 고른 사람이 공에 가장 가까운 비율 : {m:.1%} "
              f"({sum(r['match'] for r in multi)}/{len(multi)})")
        print(f"     불일치 margin (키높이) : 중앙 {statistics.median(marg):.2f} "
              f"· p75 {pct(marg, .75):.2f} · 최대 {max(marg):.2f}")
        print(f"     불일치 시 고른 사람 키 ÷ 최근접 후보 키 : 중앙 "
              f"{statistics.median(ratio):.2f}")
        per = []
        for c in clips:
            mm = [r for r in c["rows"] if r["n_cands"] >= 2]
            if len(mm) >= 5:
                per.append((sum(r["match"] for r in mm) / len(mm), c["clip"]))
        print(f"     클립별 (5프레임 이상) : "
              f"{[f'{v:.0%}' for v, _ in sorted(per)]}")

    # ⑸ 45번 1회차(발목 기반)와 맞춰 본다 — 계기가 같은 것을 보는가
    print("\n⑸ 45번 1회차(발목·어깨너비)와 대조 — 고른 사람 기준")
    prev = {r["clip"]: r for r in json.loads(PREV.read_text("utf-8"))}
    pairs = []
    for c in clips:
        p = prev.get(c["clip"], {})
        if c.get("d_chosen_ungated_median") and p.get("distance_median"):
            pairs.append((c["clip"], c["d_chosen_ungated_median"], p["distance_median"]))
    print(f"     {'클립':34s} {'이번(키높이)':>12s} {'1회차(어깨너비)':>16s}")
    for name, mine, theirs in sorted(pairs, key=lambda x: x[1]):
        print(f"     {name[:34]:34s} {mine:12.2f} {theirs:16.2f}")


if __name__ == "__main__":
    main()
