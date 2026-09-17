#!/usr/bin/env python3
"""R2′ — **경계 숫자 누출**을 센다 (미결 23번 가-2, 사전 등록 5절).

    uv run python eval/pending23_evidence/check_boundaries.py evidence_plain_after.json

🔴 **기존 R2 를 고치지 않고 더한 것이다.** `check_evidence.py` 의 R2 는
`a~b` — **두 수를 이은 표기**만 본다. 그런데 2026.09.17 판독에서 이런 문장이
나왔다:

    "임팩트 시 디딤발 무릎각 140.2도로 **기준 상한 170도 미만**이지만 …"

`170` 은 그 항목의 밴드 경계인데 **단일 숫자**라 R2 를 피하고, 합격선이 없는
R3(지어낸 수치, 보고만)로 샌다. 즉 **합격선이 있는 기준을 비껴가는 샘길**이
있었다.

R2 정규식 자체는 **안 고친다** — 그건 앞선 회차의 판정 기준이고, "결과를 보고
정규식을 고치지 않는다"가 거기에도 걸린다. 그래서 **더한다.**

## 세는 것

문장의 숫자 토큰 중, 그 항목의 **밴드 경계값**(모든 등급의 유한한 `lo`·`hi`)과
같으면서 **준 측정값과는 다른** 것. 측정값과의 비교는 R3 와 같은 허용오차
`0.55` 를 쓴다 — 141.7 을 "142도"라고 쓴 것을 누출로 세지 않기 위해서다.

🔴 **측정값이 마침 경계와 같으면 세지 않는다.** 그건 모델이 베낀 것이 아니라
준 값을 쓴 것이다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import discover_rubrics  # noqa: E402

NUMBER = re.compile(r"\d+(?:\.\d+)?")
TOLERANCE = 0.55  # R3 와 같은 값 — 반올림 표기를 누출로 세지 않는다


def boundaries(criterion) -> set[float]:
    """그 항목의 밴드 경계값 전부 (모든 등급, 유한한 것만)."""
    out: set[float] = set()
    for intervals in criterion.bands.values():
        for lo, hi in intervals:
            for edge in (lo, hi):
                if edge is not None:
                    out.add(float(edge))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        path = HERE / args.path
    data = json.loads(path.read_text(encoding="utf-8"))

    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    hits: list[tuple[str, str, list[str]]] = []
    total = 0

    for clip, payload in data["clips"].items():
        rubric = rubrics[clip]
        by_id = {c.id: c for c in rubric.criteria}
        for item in payload["items"]:
            total += 1
            crit = by_id.get(item["criterion_id"])
            if crit is None:
                continue
            edges = boundaries(crit)
            given = [float(v) for v in item["given_metrics"].values()
                     if isinstance(v, (int, float))]
            leaked = []
            for token in NUMBER.findall(item["evidence"]):
                n = float(token)
                if not any(abs(n - e) <= 1e-9 for e in edges):
                    continue
                # 준 측정값이면 베낀 것이 아니다.
                if any(abs(n - v) <= TOLERANCE for v in given):
                    continue
                leaked.append(token)
            if leaked:
                hits.append(
                    (f"{clip}/{crit.id}({item['grade']})", item["evidence"], leaked)
                )

    print(f"{data['tag']} · {total}문장")
    print(f"  R2′ 경계 숫자 누출 : {len(hits)}건   (합격선 0)")
    if args.show:
        for where, text, leaked in hits:
            print(f"  - {where}: {leaked}\n    {text}")
    print(f"\nR2′ 판정: {'합격' if not hits else '불합격'}")


if __name__ == "__main__":
    main()
