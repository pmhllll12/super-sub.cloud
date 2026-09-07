#!/usr/bin/env python3
"""저장된 측정값으로 **근거 문장만** 다시 만든다 (미결 23번).

    uv run python eval/pending23_evidence/rejudge.py --tag before
    uv run python eval/pending23_evidence/rejudge.py --tag after

포즈를 다시 뽑지 않는다 — `realclip/*_result.json`의 `features`를 그대로 판정기에
넣는다. 그래서 같은 입력에 대해 **문장만** 어떻게 달라지는지 볼 수 있고, GPU도
EXAONE 1.2B(bf16 2.4GB) 하나만 쓴다.

🔴 **등급이 저장된 결과와 다르면 그 자리에서 멈춘다.** 이 회차는 문장을 고치는
것이지 판정을 고치는 것이 아니다. 등급이 움직였다면 판정 입력이 바뀐 것이므로
사전 등록 4절대로 중단하고 원인부터 본다.

조사 스크립트라 `src/`를 고치지 않는다 — production을 import만 한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.judge import Judge, select_metrics  # noqa: E402
from supersub_agent.scoring import aggregate, load_rubric  # noqa: E402

REALCLIP = ROOT / "eval/jhmdb_batting/realclip"
RUBRIC = ROOT / "rubrics/baseball_batting.yaml"


def main() -> None:
    ap = argparse.ArgumentParser()
    # after2 = 앵커에 수준 낱말을 되살린 2회차 (사전 등록 부기 A).
    # **검사기(check_evidence.py)는 손대지 않는다** — 같은 R1·R2로 판정한다.
    ap.add_argument("--tag", required=True,
                    choices=("before", "after", "after2"),
                    help="코드를 고치기 전/후 어느 회차인가")
    args = ap.parse_args()

    rubric = load_rubric(RUBRIC)
    judge = Judge()
    print(f"백엔드: {judge.backend} · 모델: {judge.model_id}")
    judge.load()

    out: dict[str, dict] = {}
    mismatches: list[str] = []
    try:
        for path in sorted(REALCLIP.glob("*_result.json")):
            clip = path.name.replace("_result.json", "")
            data = json.loads(path.read_text(encoding="utf-8"))
            features = data["features"]
            stored = {b["criterion_id"]: b for b in data["result"]["breakdown"]}

            expected = [c.id for c in rubric.applicable_criteria(features)]
            judgments = judge.judge_all(rubric, features)
            result = aggregate(judgments, rubric, expected_ids=expected)

            # 무효화 확인 — 문장만 바뀌어야 한다.
            if result["score"] != data["result"]["score"]:
                mismatches.append(
                    f"{clip}: 총점 {data['result']['score']} → {result['score']}"
                )
            items = []
            for b in result["breakdown"]:
                cid = b["criterion_id"]
                was = stored[cid]["grade"]
                if was != b["grade"]:
                    mismatches.append(f"{clip}/{cid}: 등급 {was} → {b['grade']}")
                criterion = rubric.get(cid)
                items.append({
                    "criterion_id": cid,
                    "name": b["name"],
                    "grade": b["grade"],
                    "stored_grade": was,
                    "evidence": b["evidence"],
                    "metric_ref": b["metric_ref"],
                    # R3(지어낸 수치) 판정에 쓸, 이 항목이 모델에게 준 숫자들.
                    "given_metrics": select_metrics(criterion, features),
                })
            out[clip] = {"score": result["score"], "grade": result["grade"],
                         "items": items}
            print(f"  {clip}: {len(items)}문장 · 총점 {result['score']}")
    finally:
        judge.unload()

    dest = HERE / f"evidence_{args.tag}.json"
    dest.write_text(
        json.dumps({"tag": args.tag, "backend": judge.backend,
                    "model": judge.model_id, "clips": out},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total = sum(len(c["items"]) for c in out.values())
    print(f"\n{len(out)}클립 {total}문장 → {dest.relative_to(ROOT)}")

    if mismatches:
        print("\n🔴 등급/총점이 저장된 결과와 다르다 — 사전 등록 4절대로 중단한다:")
        for m in mismatches:
            print(f"  - {m}")
        raise SystemExit(1)
    print("등급·총점 저장된 결과와 전부 일치 (문장만 달라졌다).")


if __name__ == "__main__":
    main()
