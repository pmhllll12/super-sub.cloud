#!/usr/bin/env python3
"""사후 관찰 — **이 계기가 무엇을 볼 수 있었나** (미결 18번 10회차).

    uv run python eval/pending18_link/posthoc_reach.py    # GPU 불필요

🔴 **판정에 쓰지 않는다.** 사전 등록 판정은 `measure_link.py` 가 낸
「(다) 판별불가 — 섞여 있다」이고, 여기서 바꾸지 않는다. 8회차의 교훈대로
사후 값은 **옆에 붙여 두고 사전으로 승격하지 않는다.**

묻는 것 둘:

1. **주 층이 커버리지 붕괴를 보고 있는가** — 재획득으로 끝난 구간만 볼 수
   있는 계기다. 붕괴가 재획득으로 안 끝나면 **이 계기는 그 현상에 닿지
   못한다.** 잃은 프레임 중 주 층이 설명하는 몫을 센다
2. **섞임이 잡음인가 두 덩어리인가** — `reach`(프레임당 상자폭 이동)가
   연속이면 문턱 근처의 흔들림이고, 갈라져 있으면 **성질이 다른 두 사건**이다
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval/pending18_link"))

from measure_link import (  # noqa: E402  (경로를 여는 것이 이 import 다)
    EXTRA, LINK_IOU, gate, ladder, run_clip,
)
from measure_appearance import BOXES  # noqa: E402
from measure_conservative import calibrate  # noqa: E402
from measure_coverage import TARGET7, build_samples  # noqa: E402


def main() -> None:
    main_s, held_s = build_samples()
    K = calibrate()
    pool = {c: (b, a) for c, b, a, _ in main_s + held_s}

    rows = []
    for name, clips in (("A", [c for c in TARGET7 if c in pool]),
                        ("B", [c for c in pool if c not in TARGET7]),
                        ("C", [EXTRA] if EXTRA in BOXES else [])):
        for clip in clips:
            box, at_ms = (BOXES[clip] if name == "C" else pool[clip])
            r = run_clip(clip, box, at_ms, K)
            if r is not None:
                r["layer"] = name
                rows.append(r)

    kept = [r for r in rows if gate(r)]
    links = [lk for r in kept for lk in r["links"]]
    orphans = [(r["clip"], x) for r in kept for x in r["orphans"]]
    cap, primary = ladder(links)

    lost_reacq = sum(lk["run_len"] for lk in links)
    lost_orph = sum(x for _c, x in orphans)
    lost_all = lost_reacq + lost_orph
    lost_pri = sum(lk["run_len"] for lk in primary)

    print("═" * 100)
    print("1) 🔴 이 계기가 커버리지 붕괴에 닿는가 — 잃은 프레임의 몫")
    print("═" * 100)
    print(f"  관문 통과 클립의 잃은 프레임 …………………… {lost_all:6d}")
    print(f"    재획득으로 끝난 구간 {len(links):2d}건 ………………… {lost_reacq:6d} "
          f"({lost_reacq / lost_all:.0%})")
    print(f"    🔴 안 끝난 구간 {len(orphans):2d}건 ………………………… {lost_orph:6d} "
          f"({lost_orph / lost_all:.0%})")
    print(f"    ✅ **주 층(≤{cap}프레임) {len(primary)}건이 설명하는 몫** …… {lost_pri:6d} "
          f"({lost_pri / lost_all:.1%})")
    print("\n  구간 길이 중앙 — 재획득으로 끝난 것 "
          f"{st.median([lk['run_len'] for lk in links]):.0f}프레임 대 "
          f"안 끝난 것 {st.median([x for _c, x in orphans]):.0f}프레임")
    print("\n  안 끝난 구간 (이 계기가 못 보는 것):")
    for clip, x in sorted(orphans, key=lambda p: -p[1]):
        print(f"    {clip:16s} {x:5d}프레임")

    print("\n" + "═" * 100)
    print("2) 섞임이 잡음인가 두 덩어리인가 — `reach` (프레임당 상자폭 이동)")
    print("═" * 100)
    for lk in sorted(primary, key=lambda x: x["reach"]):
        kind = "같은 자리" if lk["reach"] < 0.5 else "🔴 순간이동"
        print(f"  {lk['clip']:16s} 길이{lk['run_len']:3d} "
              f"reach {lk['reach']:6.2f}  link_iou {lk['link_iou']:5.2f} "
              f"{'이어짐' if lk['link_iou'] >= LINK_IOU else '안이어짐':>8s}  {kind}")
    near = [lk["reach"] for lk in primary if lk["reach"] < 0.5]
    far = [lk["reach"] for lk in primary if lk["reach"] >= 0.5]
    if near and far:
        print(f"\n  🔴 사이가 비어 있다 — 아래 무리 최대 {max(near):.2f} · "
              f"위 무리 최소 {min(far):.2f} ({len(near)}건 대 {len(far)}건)")
        print("  연속이 아니라 **성질이 다른 두 사건**으로 보인다. "
              "🔴 사후 관찰이라 판정에 안 쓴다 — 표본 "
              f"{len(primary)}건이고 문턱(0.5)을 값을 보고 그었다.")


if __name__ == "__main__":
    main()
