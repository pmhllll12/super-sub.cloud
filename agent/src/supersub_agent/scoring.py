"""루브릭 적재와 점수 합산.

설계 원칙: **총점은 언어 모델이 아니라 이 모듈이 계산한다.**
모델은 항목별 0/1/2 등급만 판정하고, 가중합은 결정론적 코드가 수행한다.
따라서 같은 판정에서는 언제나 같은 점수가 나오고, 가중치를 조정해도
재분석 없이 재계산된다.
"""

from __future__ import annotations

from collections.abc import Iterable
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

    def is_applicable(self, features: dict[str, Any]) -> bool:
        """이 항목을 판정할 근거 지표가 모두 측정됐는지.

        도구 기반 지표는 공이 검출되지 않은 영상에서 빠진다. 그런 항목은 판정하지
        않고 가중치에서도 제외한다 — 측정하지 못한 것을 0점으로 매기면 촬영
        조건이 나빴다는 이유로 선수가 감점된다.
        """
        return all(m in features for m in self.measured_by)

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
    # 임팩트를 정의할 사지 — "leg"(축구 슈팅) 또는 "arm"(농구 슛·테니스 스트로크).
    # 루브릭이 선언하고 features.extract_features가 따른다.
    impact_limb: str = "leg"
    # 임팩트로 삼을 사건 — "extension_peak"(채찍질) 또는 "distal_apex"(들어올림).
    impact_event: str = "extension_peak"
    # 화면 표기용 한글 이름. 없으면 sport·motion을 그대로 쓴다.
    sport_ko: str = ""
    motion_ko: str = ""
    # 이 루브릭으로 실제 영상을 끝까지 돌려 본 근거. 비어 있으면 미검증이다.
    # 임계값이 임시값인 것(review_required)과는 다른 문제다 — 이쪽은 파이프라인이
    # 그 종목 영상에서 지표를 뽑을 수 있는지 자체를 확인했는가를 뜻한다.
    validated_on: str = ""

    @property
    def key(self) -> str:
        """루브릭 식별자 "종목/동작". 루브릭은 (종목, 동작) 단위로 하나씩 있다."""
        return f"{self.sport}/{self.motion}"

    @property
    def label(self) -> str:
        """사람이 읽을 이름. UI의 종목 선택이 이걸 쓴다."""
        return f"{self.sport_ko or self.sport} · {self.motion_ko or self.motion}"

    @property
    def criterion_ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.criteria)

    def get(self, criterion_id: str) -> Criterion:
        for c in self.criteria:
            if c.id == criterion_id:
                return c
        raise KeyError(criterion_id)

    def applicable_criteria(self, features: dict[str, Any]) -> tuple[Criterion, ...]:
        """이번 영상에서 판정 가능한 항목만 고른다.

        도구가 검출되지 않으면 그 도구를 쓰는 항목이 빠지고, 남은 항목들로만
        가중치를 재정규화해 총점을 낸다 (aggregate 참고).
        """
        applicable = tuple(c for c in self.criteria if c.is_applicable(features))
        if not applicable:
            raise RubricError("판정 가능한 항목이 하나도 없음 — 측정값이 비었다")
        return applicable

    def required_metrics(self) -> set[str]:
        """모든 항목이 근거로 삼는 지표 이름의 합집합."""
        return {m for c in self.criteria for m in c.measured_by}


def discover_rubrics(directory: str | Path) -> dict[str, Rubric]:
    """디렉터리의 루브릭을 모두 읽어 "sport/motion" 키로 돌려준다.

    루브릭 추가가 코드 변경이 아니라 **파일 추가**가 되도록 하는 진입점이다.
    파일명이 아니라 파일 안의 sport·motion을 키로 삼는다 — 이름과 내용이
    어긋나는 것을 막는다.
    """
    found: dict[str, Rubric] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        rubric = load_rubric(path)
        if rubric.key in found:
            raise RubricError(
                f"루브릭 키 중복 {rubric.key!r}: {path.name}. "
                "sport·motion 조합은 파일마다 고유해야 한다."
            )
        found[rubric.key] = rubric
    if not found:
        raise RubricError(f"루브릭을 찾지 못함: {directory}")
    return found


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
        impact_limb=_parse_choice(raw, "impact_limb", ("leg", "arm")),
        impact_event=_parse_choice(
            raw, "impact_event", ("extension_peak", "distal_apex")
        ),
        sport_ko=raw.get("sport_ko", ""),
        motion_ko=raw.get("motion_ko", ""),
        validated_on=raw.get("validated_on", ""),
    )


def _parse_choice(raw: dict[str, Any], field_name: str, allowed: tuple[str, ...]) -> str:
    """kinematics 블록의 열거형 필드를 읽고 검증한다.

    기본값은 allowed의 첫 값이다 — 이 필드들이 생기기 전에 쓴 루브릭이 그대로
    동작해야 하므로, 옛 동작(다리·신전 각속도)을 첫 값으로 둔다.
    """
    value = (raw.get("kinematics") or {}).get(field_name, allowed[0])
    if value not in allowed:
        raise RubricError(
            f"kinematics.{field_name}은 {list(allowed)} 중 하나여야 한다: {value!r}"
        )
    return value


def aggregate(
    judgments: dict[str, dict[str, Any]],
    rubric: Rubric,
    expected_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """항목별 판정을 총점으로 합산한다.

    judgments: {criterion_id: {"grade": int, "evidence": str, "metric_ref": str}}
    """
    unknown = judgments.keys() - set(rubric.criterion_ids)
    if unknown:
        raise ValueError(f"루브릭에 없는 항목의 판정: {sorted(unknown)}")

    # expected_ids를 주면 그 목록은 반드시 다 채워져 있어야 한다. 도구 미검출로
    # 빠지는 것과 판정이 실패해 빠지는 것을 구분하기 위한 장치다 — 주지 않으면
    # 없는 항목이 조용히 제외되므로, 파이프라인은 항상 넘긴다.
    if expected_ids is not None:
        missing = set(expected_ids) - judgments.keys()
        if missing:
            raise ValueError(f"판정이 누락된 항목: {sorted(missing)}")

    judged = [c for c in rubric.criteria if c.id in judgments]
    if not judged:
        raise ValueError("판정이 하나도 없음")

    # 판정된 항목만으로 가중치를 재정규화한다. 도구 미검출로 빠진 항목이 있어도
    # 남은 항목의 상대 비중이 유지되고 총점은 100점 만점을 지킨다.
    # 빠진 항목을 0점으로 두면 촬영 조건 때문에 선수가 감점된다.
    total_weight = sum(c.weight for c in judged)
    if total_weight <= 0:
        raise ValueError("판정된 항목의 가중치 합이 0")

    ratio = 0.0
    breakdown = []
    for c in judged:
        j = judgments[c.id]
        grade = int(j["grade"])
        if grade not in (0, 1, 2):
            raise ValueError(f"{c.id}: 등급은 0/1/2만 허용, 받은 값 {grade}")
        weight = c.weight / total_weight
        contribution = weight * (grade / MAX_GRADE)
        ratio += contribution
        breakdown.append(
            {
                "criterion_id": c.id,
                "name": c.name,
                "grade": grade,
                "weight": round(weight, 4),
                "contribution": round(contribution * 100, 1),
                "evidence": j.get("evidence", ""),
                "metric_ref": j.get("metric_ref", ""),
            }
        )

    skipped = [
        {"criterion_id": c.id, "name": c.name, "weight": c.weight}
        for c in rubric.criteria
        if c.id not in judgments
    ]

    score = round(ratio * 100)
    return {
        "score": score,
        "grade": _band(score, rubric.grade_bands),
        "breakdown": breakdown,
        # 측정하지 못해 판정에서 빠진 항목 — 0점이 아니라 제외다.
        "skipped": skipped,
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
