#!/usr/bin/env python3
"""`verify_pick.py` 산출들을 한 표로 모은다 — **얼마나 자주 갈아타는가**.

    uv run python eval/subject_pick/summarize_picks.py <폴더>

## 무엇을 세는가

정답이 없으므로 **정답 없이 셀 수 있는 것만** 센다.

| 세는 것 | 정답이 필요한가 |
|---|---|
| 닻에서 찍은 박스와 겹쳤는가 (`anchor_iou`) | 불필요 — 두 박스의 기하다 |
| 자동과 지정이 갈렸는가 (`differing`) | 불필요 |
| 넓이가 크게 뛴 자리가 있는가 (`area_jumps`) | 불필요 |
| **그 점프가 정말 다른 사람으로 간 것인가** | 🔴 **필요하다 — 여기서 답하지 않는다** |

마지막 줄이 요점이다. `area_jumps`는 **의심 신호**이고, 그것이 실제 갈아탐과
맞는지는 클립을 그려서 사람이 봐야 한다. 이 표는 "몇 건이 의심되는가"까지다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    args = ap.parse_args()

    rows = []
    for path in sorted(args.folder.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        auto, picked = d["auto"], d["picked"]
        n = picked.get("frames") or 1
        rows.append({
            "clip": path.stem,
            "frames": n,
            "source": picked["source"],
            "anchor_iou": picked.get("anchor_iou"),
            "anchor_frame": picked.get("anchor_frame"),
            "differing": d.get("differing_frames", 0),
            "differing_pct": round(100 * d.get("differing_frames", 0) / n),
            "jumps_picked": picked.get("area_jumps", 0),
            "jumps_auto": auto.get("area_jumps", 0),
            "breaks": picked.get("continuity_breaks", 0),
            "boxed": picked.get("frames_with_box", 0),
        })

    if not rows:
        raise SystemExit(f"결과가 없다: {args.folder}")

    head = (f"{'clip':<14}{'프레임':>6}{'source':>22}{'닻IoU':>7}"
            f"{'갈림':>8}{'점프(지정)':>10}{'점프(자동)':>10}{'끊김':>6}")
    print(head)
    print("-" * len(head))
    for r in rows:
        iou = "—" if r["anchor_iou"] is None else f"{r['anchor_iou']:.3f}"
        print(f"{r['clip']:<14}{r['frames']:>6}{r['source']:>22}{iou:>7}"
              f"{r['differing_pct']:>7}%{r['jumps_picked']:>10}"
              f"{r['jumps_auto']:>10}{r['breaks']:>6}")

    n = len(rows)
    matched = [r for r in rows if r["source"].startswith("specified")]
    uncertain = [r for r in matched if r["source"] == "specified_uncertain"]
    fallback = [r for r in rows if r["source"] == "fallback"]
    breaks_but_clean = [r for r in matched if r["breaks"] > 0 and r["jumps_picked"] == 0]
    jumps_no_breaks = [r for r in matched if r["jumps_picked"] > 0 and r["breaks"] == 0]

    print(f"\n클립 {n}건")
    print(f"  닻에서 찾음            {len(matched)}/{n}")
    print(f"  못 찾아 자동으로 떨어짐 {len(fallback)}/{n}")
    if matched:
        print(f"  🔴 갈아탄 의심          {len(uncertain)}/{len(matched)} "
              f"(찾은 것 중 {100 * len(uncertain) / len(matched):.0f}%)")
    print(f"\n  🔴 끊김은 0인데 점프가 있는 클립: {len(jumps_no_breaks)}건 "
          "— continuity_breaks 가 못 잡는 것들이다")
    print(f"     점프는 0인데 끊김이 있는 클립: {len(breaks_but_clean)}건 "
          "— 두 신호가 다른 것을 본다는 뜻이다")
    print("\n🔴 이 표는 '몇 건이 의심되는가'까지다. 그 의심이 실제 갈아탐과 "
          "맞는지는\n   클립을 그려서 사람이 봐야 한다 — 정답이 없다.")


if __name__ == "__main__":
    main()
