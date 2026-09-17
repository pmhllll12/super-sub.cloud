#!/usr/bin/env python3
"""양방향 구간 항목의 근거 문장을 **사람이 읽도록** 나란히 찍는다 (미결 23번 (나)).

    uv run python eval/pending23_evidence/two_way_bands.py

🔴 **판정하지 않는다.** 이 스크립트는 「어느 문장을 사람이 읽어야 하는가」를
고르기만 한다. "감점을 칭찬으로 서술했는가"는 문장 **뜻**의 문제라 문자열로
가를 수 없고, 가르려 하면 그 검사가 또 틀린다(미결 23번이 처음부터 적어 둔
「하지 말 것」이다). 그래서 세지 않고 **띄워 준다.**

왜 하필 양방향 구간인가 — 2026.09.17 판독에서 방향 오독 3건이 **전부** 그
근처였다. 기전이 있다:

    build_prompt 는 세 등급의 `grades[g]` 를 전부 프롬프트에 넣는다.
    양방향 구간의 `grades[g]` 는 두 방향을 **한 문자열**에 담는다 —
    "170도 초과(굴곡 부족) 또는 135~150도(과굴곡)".
    측정값이 어느 쪽인지는 안 알려 준다. **모델이 고른다.**

미결 50번이 2026.09.16 에 `titles`·`card_lines` 를 구간마다 갈랐는데, 그건
**코드가 고르는** 문구다. **모델이 읽는 `grades` 는 안 갈랐다** — 그래서
카드 문장은 방향이 맞고 근거 문장은 틀릴 수 있다.

🔴 **어느 방향인지 이 스크립트가 정답을 주지는 않는다.** 측정값이 어느 조각에
들어가는지는 찍어 주지만, 그 문장이 그 방향으로 말했는지는 읽어야 안다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent
sys.path.insert(0, str(AGENT / "src"))

LEVEL = {2: "잘함", 1: "보통", 0: "아쉬움"}


def segments(band) -> list:
    """등급 하나의 구간 조각들. 한 조각이면 단방향이다."""
    if not band:
        return []
    return band if isinstance(band[0], list) else [band]


def which_segment(value, segs) -> int | None:
    """측정값이 몇 번째 조각에 들어가는가. 못 정하면 None."""
    if value is None:
        return None
    for i, (lo, hi) in enumerate(segs):
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return i
    return None


def main() -> None:
    data = json.loads(
        (HERE / "evidence_football.json").read_text(encoding="utf-8")
    )

    flagged = 0
    total = 0
    for clip, payload in data["clips"].items():
        key = clip.split("/")[1]
        rubric = yaml.safe_load(
            (AGENT / "rubrics" / f"football_{key}.yaml").read_text(encoding="utf-8")
        )
        by_id = {c["id"]: c for c in rubric["criteria"]}

        header_done = False
        for item in payload["items"]:
            total += 1
            crit = by_id.get(item["criterion_id"])
            if not crit:
                continue
            grade = item["grade"]
            segs = segments(crit["bands"].get(grade))
            if len(segs) < 2:
                continue  # 단방향 — 모델이 고를 일이 없다

            if not header_done:
                print(f"\n{'=' * 72}\n## {clip}")
                header_done = True

            flagged += 1
            value = item["given_metrics"].get(crit["bands"]["metric"])
            idx = which_segment(value, segs)
            titles = crit.get("titles", {}).get(grade)
            titles = titles if isinstance(titles, list) else [titles]
            said = titles[idx] if idx is not None and idx < len(titles) else "?"

            print(f"\n[{LEVEL[grade]}] {crit['name']} · 측정 {value}")
            print(f"  구간 조각 : {segs}  → {idx}번 조각")
            print(f"  코드가 고른 말 : 「{said}」")
            print(f"  수준 정의(프롬프트에 그대로 들어간다) : {crit['grades'][grade]}")
            print(f"  모델이 쓴 문장 : {item['evidence']}")

    print(f"\n{'=' * 72}")
    print(f"전체 {total}문장 중 **양방향 구간에 앉은 것 {flagged}문장**.")
    print("🔴 위 문장들을 사람이 읽고 방향이 맞는지 본다 — 이 스크립트는 안 센다.")


if __name__ == "__main__":
    main()
