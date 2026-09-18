#!/usr/bin/env python3
"""BASE 와 파인튜닝 결과를 **같은 자리에서** 나란히 놓는다 (사전 등록 4·5절).

    uv run python eval/pending23_finetune/compare.py \
        --base base_inside_pass.json --after evidence_finetuned.json

자동으로 세는 것은 **P-3(R1·R2) · P-4(R3) · P-5(고유 문장 가짓수)** 뿐이다.
🔴 **P-1·P-2(방향 오독)는 여기서 안 센다** — 문자열로 가르려 하면 그 검사가
또 틀린다(미결 23번). 절 단위로 사람이 읽을 수 있게 **나란히 찍기만** 한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "eval/pending23_evidence"))

from check_evidence import RANGE, hallucinated_numbers  # noqa: E402

EVAL = "football/inside_pass"


def items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["clips"][EVAL]["items"]


def tally(rows: list[dict]) -> dict:
    r1 = [i for i in rows if "등급" in i["evidence"]]
    r2 = [i for i in rows if RANGE.search(i["evidence"])]
    r3 = [i for i in rows
          if hallucinated_numbers(i["evidence"], i["given_metrics"])]
    uniq = {re.sub(r"[\d.]+", "#", i["evidence"]) for i in rows}
    return {"n": len(rows), "R1": len(r1), "R2": len(r2), "R3": len(r3),
            "고유(수치 가린 뒤)": len(uniq),
            "고유(그대로)": len({i["evidence"] for i in rows})}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="base_inside_pass.json")
    ap.add_argument("--after", default="evidence_finetuned.json")
    args = ap.parse_args()

    base = {(i["criterion_id"], i["grade"], i["segment"], i["value"]): i
            for i in items(HERE / args.base)}
    after = {(i["criterion_id"], i["grade"], i["segment"], i["value"]): i
             for i in items(HERE / args.after)}
    assert set(base) == set(after), "자리가 다르다 — 비교할 수 없다"

    for key in sorted(base, key=lambda k: (k[0], -k[1], k[2], k[3])):
        b, a = base[key], after[key]
        head = "감점" if b["grade"] < 2 else "잘함"
        print(f"\n### [{head}] {b['name']} · {b['grade']}등급 · 조각 {b['segment']}"
              f" · 값 {b['value']}")
        print(f"    🎯 코드: {b['plain'] or '(없음)'}")
        print(f"    BASE : {b['evidence']}")
        print(f"    FT   : {a['evidence']}")

    print("\n" + "=" * 60)
    for name, rows in (("BASE", list(base.values())), ("FT", list(after.values()))):
        print(f"{name}: {tally(rows)}")
    ded = [k for k in base if k[1] < 2]
    print(f"감점 자리 {len(ded)} · 잘함 자리 {len(base) - len(ded)} "
          "— 방향 오독은 사람이 센다 (사전 등록 5절)")


if __name__ == "__main__":
    main()
