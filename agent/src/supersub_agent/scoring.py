"""루브릭 적재와 점수 합산.

설계 원칙: **총점은 언어 모델이 아니라 이 모듈이 계산한다.**
모델은 항목별 0/1/2 등급만 판정하고, 가중합은 결정론적 코드가 수행한다.
따라서 같은 판정에서는 언제나 같은 점수가 나오고, 가중치를 조정해도
재분석 없이 재계산된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

MAX_GRADE = 2

# 등급 판정 구간 (최소, 최대). None은 한쪽이 열린 구간을 뜻한다.
Interval = tuple[float | None, float | None]


class RubricError(ValueError):
    """루브릭 정의 자체가 잘못된 경우."""


def _parse_bands(entry: dict[str, Any]) -> tuple[str, dict[int, tuple[Interval, ...]]]:
    """루브릭 항목의 bands 블록을 파싱하고 검증한다."""
    raw = entry.get("bands")
    if not raw:
        raise RubricError(
            f"{entry['id']}: bands 없음. 등급은 코드가 구간으로 판정하므로 "
            "모든 항목에 bands가 있어야 한다."
        )

    metric = raw.get("metric")
    if metric not in entry.get("measured_by", []):
        raise RubricError(
            f"{entry['id']}: bands.metric {metric!r}가 measured_by에 없음. "
            "판정 근거가 아닌 지표로 등급을 정할 수 없다."
        )

    bands: dict[int, tuple[Interval, ...]] = {}
    for grade in (0, 1, 2):
        if grade not in raw:
            raise RubricError(f"{entry['id']}: bands에 {grade}등급 구간 누락")
        intervals: list[Interval] = []
        for pair in raw[grade]:
            if len(pair) != 2:
                raise RubricError(f"{entry['id']}: {grade}등급 구간 형식 오류 {pair!r}")
            lo, hi = pair
            lo = None if lo is None else float(lo)
            hi = None if hi is None else float(hi)
            if lo is not None and hi is not None and lo > hi:
                raise RubricError(f"{entry['id']}: {grade}등급 구간 역전 {pair!r}")
            intervals.append((lo, hi))
        if not intervals:
            raise RubricError(f"{entry['id']}: {grade}등급 구간이 비어 있음")
        bands[grade] = tuple(intervals)

    return metric, bands


@dataclass(frozen=True)
class Criterion:
    id: str
    name: str
    weight: float
    measured_by: tuple[str, ...]
    grades: dict[int, str]
    anchors: tuple[dict[str, Any], ...]
    rationale: str = ""
    # 등급별 칭호 — 선수에게 보여줄 짧은 표현. 채점에는 관여하지 않는다.
    # 지도자가 검수하는 문구이므로 UI가 아니라 루브릭에 둔다.
    titles: dict[int, str] = field(default_factory=dict)
    # 등급 판정 구간. band_metric 하나의 값으로 등급이 결정된다.
    band_metric: str = ""
    bands: dict[int, tuple[Interval, ...]] = field(default_factory=dict)

    def title_for(self, grade: int) -> str:
        """해당 등급의 칭호. 정의되지 않았으면 항목명으로 대체한다."""
        return self.titles.get(grade) or self.name

    def grade_for(self, features: dict[str, Any]) -> int:
        """측정값을 구간과 대조해 등급을 결정한다.

        **등급은 언어 모델이 아니라 이 함수가 정한다.** 루브릭의 등급 정의가
        이미 수치 구간이므로 판정에 추론이 필요 없다. EXAONE 1.2B는 실제로
        141.7이 140~165 범위 안이라는 비교를 틀렸다(재현되는 오답).

        구간은 양끝을 포함하고, 2 → 1 → 0 순으로 먼저 맞는 등급을 취한다.
        경계값(예: 150)이 두 등급에 걸치면 높은 등급으로 간다.
        """
        if self.band_metric not in features:
            raise RubricError(
                f"{self.id}: 등급 판정 지표 {self.band_metric!r}가 측정값에 없음"
            )
        value = float(features[self.band_metric])
        for grade in (2, 1, 0):
            for lo, hi in self.bands[grade]:
                if (lo is None or value >= lo) and (hi is None or value <= hi):
                    return grade
        raise RubricError(
            f"{self.id}: {self.band_metric}={value}가 어느 등급 구간에도 없음. "
            "루브릭 bands가 값 범위를 모두 덮지 않는다."
        )


@dataclass(frozen=True)
class Rubric:
    sport: str
    motion: str
    version: str
    criteria: tuple[Criterion, ...]
    grade_bands: dict[str, int]
    review_required: bool
    pipeline_version: str

    @property
    def criterion_ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.criteria)

    def get(self, criterion_id: str) -> Criterion:
        for c in self.criteria:
            if c.id == criterion_id:
                return c
        raise KeyError(criterion_id)

    def required_metrics(self) -> set[str]:
        """모든 항목이 근거로 삼는 지표 이름의 합집합."""
        return {m for c in self.criteria for m in c.measured_by}


def load_rubric(path: str | Path) -> Rubric:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    criteria: list[Criterion] = []
    for entry in raw.get("criteria", []):
        grades = {int(k): v for k, v in entry["grades"].items()}
        missing = {0, 1, 2} - grades.keys()
        if missing:
            raise RubricError(f"{entry['id']}: 등급 정의 누락 {sorted(missing)}")
        if not entry.get("measured_by"):
            raise RubricError(
                f"{entry['id']}: measured_by가 비어 있음. "
                "근거 지표가 없는 항목은 판정할 수 없다."
            )
        band_metric, bands = _parse_bands(entry)
        criteria.append(
            Criterion(
                id=entry["id"],
                name=entry["name"],
                weight=float(entry["weight"]),
                measured_by=tuple(entry["measured_by"]),
                grades=grades,
                anchors=tuple(entry.get("anchors", [])),
                rationale=entry.get("rationale", ""),
                titles={int(k): v for k, v in (entry.get("titles") or {}).items()},
                band_metric=band_metric,
                bands=bands,
            )
        )

    if not criteria:
        raise RubricError("채점 항목이 하나도 없음")

    total_weight = sum(c.weight for c in criteria)
    if abs(total_weight - 1.0) > 1e-6:
        raise RubricError(f"가중치 합이 1.0이 아님: {total_weight:.4f}")

    return Rubric(
        sport=raw["sport"],
        motion=raw["motion"],
        version=str(raw.get("version", "0")),
        criteria=tuple(criteria),
        grade_bands=raw.get("grade_bands", {"A": 85, "B": 70, "C": 50, "D": 0}),
        review_required=bool(raw.get("review_required", False)),
        pipeline_version=raw.get("pipeline_version", "unknown"),
    )


def aggregate(judgments: dict[str, dict[str, Any]], rubric: Rubric) -> dict[str, Any]:
    """항목별 판정을 총점으로 합산한다.

    judgments: {criterion_id: {"grade": int, "evidence": str, "metric_ref": str}}
    """
    missing = set(rubric.criterion_ids) - judgments.keys()
    if missing:
        raise ValueError(f"판정이 누락된 항목: {sorted(missing)}")

    ratio = 0.0
    breakdown = []
    for c in rubric.criteria:
        j = judgments[c.id]
        grade = int(j["grade"])
        if grade not in (0, 1, 2):
            raise ValueError(f"{c.id}: 등급은 0/1/2만 허용, 받은 값 {grade}")
        contribution = c.weight * (grade / MAX_GRADE)
        ratio += contribution
        breakdown.append(
            {
                "criterion_id": c.id,
                "name": c.name,
                "grade": grade,
                "weight": c.weight,
                "contribution": round(contribution * 100, 1),
                "evidence": j.get("evidence", ""),
                "metric_ref": j.get("metric_ref", ""),
            }
        )

    score = round(ratio * 100)
    return {
        "score": score,
        "grade": _band(score, rubric.grade_bands),
        "breakdown": breakdown,
        "rubric_version": rubric.version,
        "pipeline_version": rubric.pipeline_version,
        # 검수 전 루브릭으로 낸 점수는 대외 노출하지 않는다.
        "provisional": rubric.review_required,
    }


def _band(score: int, bands: dict[str, int]) -> str:
    for label, floor in sorted(bands.items(), key=lambda kv: kv[1], reverse=True):
        if score >= floor:
            return label
    return min(bands, key=lambda k: bands[k])
