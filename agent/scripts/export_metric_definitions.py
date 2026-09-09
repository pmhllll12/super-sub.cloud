#!/usr/bin/env python3
"""`metric_definition` 시드 행을 낸다 (미결 `jin` 23번).

    uv run python scripts/export_metric_definitions.py            # 표로 본다
    uv run python scripts/export_metric_definitions.py --json     # 시드용
    uv run python scripts/export_metric_definitions.py --csv

`rubrics/metric_definitions.yaml`(label·unit 의 정본)과 `rubrics/*.yaml`
(어떤 항목이 열려 있는가)를 합쳐 **적재에서 실제로 쓰이는 코드 전부**를 낸다.

🔴 **「루브릭이 쓰는 코드」보다 넓다.** 세 종류가 섞여 나간다:

  1. 측정 지표 — 루브릭 `measured_by` 가 쓰는 것
  2. `impact_frame` — **어느 루브릭도 안 쓰는데** `features` 에 실려 나간다
  3. 판정값 — `total_score` 와 항목별 등급 (계약 3-1: 「총점과 항목별 등급도
     metrics 에 넣는다」)

셋 중 하나라도 빠지면 그 코드가 `UNKNOWN_METRIC_CODE` 로 거부되고, **적재가
통째로 실패한다.** 스텁 테스트는 통과하므로 초록색에 속기 쉽다.

기본은 `active` 루브릭만이다. `--include-draft` 로 닫아 둔 것까지 낸다 —
draft 를 여는 시점에 시드를 또 손대지 않으려면 미리 넣어 두는 편이 낫다.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import load_rubric  # noqa: E402

# 🔴 `rubrics/` 안에 두지 않는다. `discover_rubrics` 가 그 폴더의 `*.yaml` 을
#    **전부 루브릭으로 읽어서** 「채점 항목이 하나도 없음」으로 죽는다. 워커의
#    `SUPERSUB_RUBRIC_DIR` 도 그 폴더를 가리킨다 — 루브릭이 아닌 파일을 거기
#    두면 배포에서 터진다. (처음에 그렇게 뒀다가 test_scoring 이 잡았다.)
DEFS = ROOT / "contracts" / "metric_definitions.yaml"
RUBRIC_DIR = ROOT / "rubrics"


def load_definitions() -> dict:
    return yaml.safe_load(DEFS.read_text(encoding="utf-8"))


def rubrics(include_draft: bool) -> list:
    out = []
    for path in sorted(RUBRIC_DIR.glob("*.yaml")):
        r = load_rubric(path)
        if r.is_active or include_draft:
            out.append(r)
    return out


def build_rows(include_draft: bool = False) -> list[dict]:
    """(code, label, unit, kind, note) 행. 순서는 종류 → 코드다."""
    defs = load_definitions()
    rows: list[dict] = []

    for m in defs["metrics"]:
        note = m.get("description", "").strip()
        if m.get("signed"):
            note = f"[부호 있음] {note}"
        if m.get("scale_ref"):
            note = f"[{m['scale_ref']} 기준 비율] {note}"
        rows.append({
            "code": m["code"], "label": m["label"], "unit": m["unit"],
            "kind": "metric", "note": note,
        })

    for j in defs["judgments"]:
        rows.append({
            "code": j["code"], "label": j["label"], "unit": j["unit"],
            "kind": "judgment", "note": j.get("description", "").strip(),
        })

    fmt = defs["grade_code_format"]
    unit = defs["grade_unit"]
    for r in rubrics(include_draft):
        for c in r.criteria:
            code = fmt.format(sport=r.sport, motion=r.motion, criterion_id=c.id)
            # 🔴 라벨에 종목을 함께 적는다. 코드당 한 행이라 「마무리」만으로는
            #    농구 것인지 축구 것인지 화면에서 못 가른다.
            rows.append({
                "code": code,
                "label": f"{r.label} · {c.name}",
                "unit": unit,
                "kind": "grade" + ("" if r.is_active else " (draft)"),
                "note": f"0~2 등급. 가중치 {c.weight}",
            })

    seen: dict[str, dict] = {}
    for row in rows:
        if row["code"] in seen and seen[row["code"]] != row:
            raise SystemExit(
                f"🔴 같은 코드가 서로 다른 정의로 두 번 나왔다: {row['code']}\n"
                f"   {seen[row['code']]}\n   {row}"
            )
        seen[row["code"]] = row
    return list(seen.values())


def check_coverage(include_draft: bool = False) -> list[str]:
    """루브릭이 쓰는데 정본에 선언되지 않은 코드. 비어 있어야 한다."""
    declared = {m["code"] for m in load_definitions()["metrics"]}
    used: set[str] = set()
    for r in rubrics(include_draft):
        used |= r.required_metrics()
    return sorted(used - declared)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="시드용 JSON")
    ap.add_argument("--csv", action="store_true", help="CSV")
    ap.add_argument("--include-draft", action="store_true",
                    help="닫아 둔(draft) 루브릭의 등급 코드까지")
    args = ap.parse_args()

    missing = check_coverage(args.include_draft)
    if missing:
        print("🔴 정본에 없는 코드를 루브릭이 쓰고 있다:", file=sys.stderr)
        for code in missing:
            print(f"   {code}", file=sys.stderr)
        print("   rubrics/metric_definitions.yaml 에 먼저 선언할 것.",
              file=sys.stderr)
        raise SystemExit(1)

    rows = build_rows(args.include_draft)

    if args.json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    if args.csv:
        w = csv.DictWriter(sys.stdout, fieldnames=["code", "label", "unit",
                                                   "kind", "note"])
        w.writeheader()
        w.writerows(rows)
        return

    by_kind: dict[str, list[dict]] = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r)
    for kind, group in by_kind.items():
        print(f"\n── {kind} ({len(group)}행)")
        for r in group:
            print(f"  {r['code']:44} {r['unit']:6} {r['label']}")
    print(f"\n총 {len(rows)}행"
          + ("" if args.include_draft else " (active 루브릭만 — draft 까지는"
                                           " --include-draft)"))


if __name__ == "__main__":
    main()
