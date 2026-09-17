#!/usr/bin/env python3
"""두 번째 지표 회차의 문장을 **지속 시간별로 나란히** 찍는다 (미결 23번).

    uv run python eval/pending23_evidence/second_metric_report.py

🔴 **판정하지 않는다.** 같은 밴드 값에 지속 시간만 1·4·11 로 바꾼 세 문장을
한 묶음으로 보여 줄 뿐이다. 「방향이 따라 움직였는가」는 **사람이 읽는다** —
문자열로 가르려 하면 그 검사가 또 틀린다(미결 23번의 「하지 말 것」).

Q3(등급이 움직였는가)만 기계가 답한다 — 그건 숫자 비교라서다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEVEL = {2: "잘함", 1: "보통", 0: "아쉬움"}


def main() -> None:
    path = HERE / (sys.argv[1] if len(sys.argv) > 1 else "evidence_second_metric.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    moved = 0
    total = 0
    for clip, payload in data["clips"].items():
        print(f"\n{'=' * 74}\n## {clip}")
        # (등급, 조각, 밴드값) 으로 묶어 지속 시간만 다른 셋을 나란히 둔다.
        groups: dict[tuple, list] = {}
        for item in payload["items"]:
            total += 1
            if item["grade"] != item["graded_as"]:
                moved += 1
            groups.setdefault(
                (item["grade"], item["segment"], item["band_value"]), []
            ).append(item)

        for (grade, seg, band_value), items in groups.items():
            print(f"\n[{LEVEL[grade]}] {items[0]['name']} · "
                  f"{seg}번 조각 · 밴드값 {band_value}")
            for item in sorted(items, key=lambda i: i["duration"]):
                print(f"  지속 {item['duration']:>5}프레임 → {item['evidence']}")

    print(f"\n{'=' * 74}")
    print(f"전체 {total}문장.")
    print(f"🔴 Q3 — 두 번째 지표가 **등급**을 움직인 건수: {moved} (0 이어야 한다)")
    print("🔴 Q1·Q2(방향이 따라 움직였는가)는 위 묶음을 사람이 읽고 답한다.")


if __name__ == "__main__":
    main()
