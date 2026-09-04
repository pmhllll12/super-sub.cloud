#!/usr/bin/env python3
"""근거 문장을 **확정된 등급·칭호·구간과 나란히** 찍는다 (미결 23번).

    uv run python eval/jhmdb_batting/realclip/evidence_audit.py

등급은 코드가 정하고 모델은 문장만 쓴다(`judge.py`). 그래서 점수는 안 틀리는데
**문장이 자기 등급을 잘못 말할 수 있다.** 그것을 읽으려면 문장 옆에 "이 등급이
무슨 뜻인지"가 함께 있어야 한다 — 문장만 보면 그럴듯해서 안 걸린다.

🔴 **판정은 사람이 한다.** 이 스크립트는 자동으로 모순을 세지 않는다. "칭찬인가
지적인가"는 문장 뜻의 문제라 문자열 검사로 가르면 그 검사가 또 틀린다.
`--only-deductions`로 0·1등급만 보면 읽을 양이 절반으로 준다 — 실측에서 결함이
전부 거기 있었다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import load_rubric  # noqa: E402

RUBRIC = ROOT / "rubrics/baseball_batting.yaml"


def band_text(criterion, grade: int) -> str:
    parts = []
    for lo, hi in criterion.bands.get(grade, ()):
        if lo is None:
            parts.append(f"~{hi:g}")
        elif hi is None:
            parts.append(f"{lo:g}~")
        else:
            parts.append(f"{lo:g}~{hi:g}")
    return " 또는 ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-deductions", action="store_true",
                    help="0·1등급만 본다 — 감점 문장이 어긋나면 피해가 크다")
    args = ap.parse_args()

    rubric = load_rubric(RUBRIC)
    shown = 0
    for path in sorted(HERE.glob("*_result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n===== {path.name.replace('_result.json', '')}")
        for item in data["result"]["breakdown"]:
            grade = int(item["grade"])
            if args.only_deductions and grade == 2:
                continue
            criterion = rubric.get(item["criterion_id"])
            print(f"\n  [{grade}등급] {criterion.name} — 「{criterion.title_for(grade)}」")
            print(f"    이 등급의 뜻 : {criterion.grades[grade]}")
            print(f"    구간         : {band_text(criterion, grade)}")
            print(f"    모델 문장    : {item['evidence']}")
            shown += 1
    print(f"\n{shown}건. 문장이 「등급의 뜻」과 반대로 말하면 그것이 결함이다.")


if __name__ == "__main__":
    main()
