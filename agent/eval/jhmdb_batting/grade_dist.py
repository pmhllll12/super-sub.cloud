#!/usr/bin/env python3
"""`analyze_keypoints.py` 결과에 타격 루브릭 구간을 대어 등급 분포를 찍는다.

    uv run python eval/jhmdb_batting/grade_dist.py \
        eval/jhmdb_batting/features_swing_baseball.json

🔴 **이 출력은 정확도가 아니다.** JHMDB의 정답은 관절이지 자세 등급이 아니라,
여기서 나오는 0/1/2 분포는 "우리 구간이 이 클립들을 어떻게 가르는가"일 뿐
"맞았는가"가 아니다. 구간을 이 분포에 맞춰 옮기지 않는다 — README 참고.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import _band, aggregate, load_rubric  # noqa: E402

RUBRIC = ROOT / "rubrics/baseball_batting.yaml"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"사용법: {sys.argv[0]} <features_*.json>")

    rubric = load_rubric(RUBRIC)
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    records = [x for x in data["records"] if "features" in x]

    print(f"측정 성공 {len(records)}/{data['counted']['clips']}")
    for x in data["records"]:
        if "features" not in x:
            print("  ✗", x["clip"], (x.get("skipped") or x.get("error"))[:90])

    per_criterion: dict[str, list[tuple[int, float]]] = {}
    scores: list[int] = []
    for x in records:
        feats = x["features"]
        judgments = {}
        for c in rubric.applicable_criteria(feats):
            grade = c.grade_for(feats)
            per_criterion.setdefault(c.id, []).append(
                (grade, float(feats[c.band_metric]))
            )
            judgments[c.id] = {"grade": grade, "evidence": "", "metric_ref": c.band_metric}
        scores.append(aggregate(judgments, rubric)["score"])

    print("\n항목별 등급 분포 · 측정값 분포")
    for cid, vals in per_criterion.items():
        grades = [g for g, _ in vals]
        measured = sorted(v for _, v in vals)
        print(
            f"  {cid:26s} n={len(vals):2d}  "
            f"0/1/2 = {grades.count(0)}/{grades.count(1)}/{grades.count(2)}"
            f"   min {measured[0]:7.1f}  중앙 {st.median(measured):7.1f}"
            f"  max {measured[-1]:7.1f}"
        )

    print(
        f"\n총점 중앙 {st.median(scores)} · 범위 {min(scores)}~{max(scores)} · "
        f"등급 {dict(Counter(_band(s, rubric.grade_bands) for s in scores))}"
    )


if __name__ == "__main__":
    main()
