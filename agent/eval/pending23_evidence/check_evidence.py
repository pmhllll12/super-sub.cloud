#!/usr/bin/env python3
"""사전 등록한 R1·R2·R3를 문장에 적용한다 (미결 23번 처방 가).

    uv run python eval/pending23_evidence/check_evidence.py evidence_after.json

| R1 | 문장에 「등급」이라는 낱말 | 합격선 0건 |
| R2 | 두 수를 이은 구간 표기(`115~140`) | 합격선 0건 |
| R3 | 준 측정값에 없는 숫자(지어낸 수치) | 합격선 없음, 보고만 |

🔴 **이 검사가 가르는 것은 표기뿐이다.** "감점을 칭찬으로 서술하는가"는 문장 뜻의
문제라 여기서 세지 않는다 — 문자열로 가르려 하면 그 검사가 또 틀리고, 틀린 검사는
"검사했다"는 인상만 남긴다(미결 23번).

판정 규칙은 문장을 만들기 전에 고정했다(PREREGISTRATION.md 3절). 결과를 보고
정규식을 고치지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 두 수를 물결·하이픈으로 이은 구간 표기. "140~165", "115-140", "18–25"
RANGE = re.compile(r"\d+(?:\.\d+)?\s*[~〜～–—\-]\s*\d+(?:\.\d+)?")
NUMBER = re.compile(r"\d+(?:\.\d+)?")

# 반올림·절사 표기를 허용한다: 141.7을 "142도"라고 써도 지어낸 수치가 아니다.
TOLERANCE = 0.55


def hallucinated_numbers(text: str, given: dict) -> list[str]:
    values = [float(v) for v in given.values() if isinstance(v, (int, float))]
    out = []
    for token in NUMBER.findall(text):
        n = float(token)
        if not any(abs(n - v) <= TOLERANCE for v in values):
            out.append(token)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="rejudge.py가 낸 evidence_*.json")
    ap.add_argument("--show", action="store_true", help="위반 문장을 전부 찍는다")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        path = HERE / args.path
    data = json.loads(path.read_text(encoding="utf-8"))

    total = 0
    r1: list[tuple[str, str, str]] = []
    r2: list[tuple[str, str, str]] = []
    r3: list[tuple[str, str, list[str]]] = []
    for clip, payload in data["clips"].items():
        for item in payload["items"]:
            total += 1
            text = item["evidence"]
            where = f"{clip}/{item['criterion_id']}({item['grade']})"
            if "등급" in text:
                r1.append((where, text, "등급"))
            found = RANGE.search(text)
            if found:
                r2.append((where, text, found.group()))
            made_up = hallucinated_numbers(text, item["given_metrics"])
            if made_up:
                r3.append((where, text, made_up))

    print(f"{data['tag']} · {data['backend']} · {total}문장")
    print(f"  R1 「등급」 표기      : {len(r1)}건   (합격선 0)")
    print(f"  R2 구간 표기          : {len(r2)}건   (합격선 0)")
    print(f"  R3 지어낸 수치        : {len(r3)}건   (보고만)")

    for label, rows in (("R1", r1), ("R2", r2), ("R3", r3)):
        if not rows or not args.show:
            continue
        print(f"\n[{label}]")
        for where, text, hit in rows:
            print(f"  - {where}: {hit}\n    {text}")

    verdict = "합격" if not r1 and not r2 else "불합격"
    print(f"\nR1·R2 판정: {verdict}")


if __name__ == "__main__":
    main()
