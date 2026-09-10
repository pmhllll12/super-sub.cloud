"""`report.json` 을 DB 적재용 구조로 옮긴다. 미결 `jin` 27번.

**순수 함수다** — S3·DB 를 모른다. 바이트를 받아 검증하고 우리 행 모양으로
바꿔 돌려준다. 그래서 픽스처 JSON 하나로 전수 검사할 수 있다.

필드 목록의 정본은 `agent/contracts/report_schema.yaml`(정상호, 미결 `jin` 27번).
봉투의 `schema_version` 이 그 계약의 버전을 싣는다.

🔴 **모르는 major 는 거부한다.** 반쯤 적재하면 어느 행이 낡은 스키마에서 온
것인지 사후에 구분할 방법이 없다(정상호 규칙). 필드가 늘기만 한 minor 변경은
모르는 키를 무시하면 되므로 통과시킨다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

# 이 코드가 아는 계약 major. `report_schema.yaml` 의 `version` 앞자리.
SUPPORTED_SCHEMA_MAJOR = 1

# 프레임 단위 지표 — `features` 의 원값은 프레임이라 `frame_metrics_seconds` 의
# 초 환산을 대신 넣는다. 격자를 모르면 `frame_metrics_seconds` 가 비어 있고,
# 그때는 그 코드를 적재하지 않는다(0 을 지어내지 않는다).
_FRAME_METRIC_CODES = frozenset({"impact_frame", "follow_through_duration_frames"})

_TOTAL_SCORE_CODE = "total_score"


class UnsupportedReportSchema(Exception):
    """봉투의 `schema_version` major 가 이 코드가 아는 값이 아니다."""


class MalformedReport(Exception):
    """JSON 이 아니거나 필수 키가 없다."""


@dataclass(frozen=True)
class MetricValueRow:
    metric_code: str
    value: Decimal
    frame_index: int | None = None


@dataclass(frozen=True)
class CriterionRow:
    criterion_id: str
    name: str
    weight: Decimal
    skipped: bool
    grade: int | None = None
    contribution: Decimal | None = None
    title: str | None = None
    band: str | None = None
    out_of_band: str = ""
    evidence: str | None = None
    metric_ref: str | None = None


@dataclass(frozen=True)
class ParsedReport:
    schema_version: str
    pipeline_version: str
    rubric_sport: str
    rubric_motion: str
    rubric_version: str
    summary: str
    model_name: str
    provisional: bool | None
    previews: dict[str, Any] | None
    keypoint_quality: dict[str, Any] | None
    metric_values: list[MetricValueRow]
    criteria: list[CriterionRow]


def _dec(x: Any) -> Decimal:
    # float → Decimal 은 str 를 거쳐야 자릿수가 안 튄다.
    return Decimal(str(x))


def _require(d: dict[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise MalformedReport(f"{where} 에 `{key}` 가 없습니다.")
    return d[key]


def parse_report(raw: bytes) -> ParsedReport:
    try:
        env = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise MalformedReport(f"JSON 이 아닙니다: {exc}") from exc
    if not isinstance(env, dict):
        raise MalformedReport("최상위가 객체가 아닙니다.")

    schema_version = str(_require(env, "schema_version", "봉투"))
    major = schema_version.split(".", 1)[0]
    if not major.isdigit() or int(major) != SUPPORTED_SCHEMA_MAJOR:
        raise UnsupportedReportSchema(
            f"이 코드는 schema_version {SUPPORTED_SCHEMA_MAJOR}.x 만 압니다 "
            f"— 받은 값 {schema_version!r}."
        )

    rubric = _require(env, "rubric", "봉투")
    sport = str(_require(rubric, "sport", "rubric"))
    motion = str(_require(rubric, "motion", "rubric"))
    rubric_version = str(rubric.get("version", ""))

    result = _require(env, "result", "봉투")
    summary = str(_require(result, "summary", "result"))
    # `model_name` 은 근거 문장(evidence)을 쓴 모델이다 — 봉투의 `judge_model`.
    model_name = str(env.get("judge_model") or "unknown")

    features: dict[str, Any] = env.get("features") or {}
    fms: dict[str, Any] = env.get("frame_metrics_seconds") or {}

    values: list[MetricValueRow] = []
    for code, value in features.items():
        if code in _FRAME_METRIC_CODES:
            if code not in fms:
                # 격자를 몰라 초 환산이 없다 — 지어내지 않는다.
                continue
            value = fms[code]
        values.append(MetricValueRow(metric_code=code, value=_dec(value)))

    values.append(
        MetricValueRow(
            metric_code=_TOTAL_SCORE_CODE,
            value=_dec(_require(result, "score", "result")),
        )
    )

    criteria: list[CriterionRow] = []
    for item in result.get("breakdown", []):
        cid = str(_require(item, "criterion_id", "breakdown 항목"))
        grade = int(_require(item, "grade", f"breakdown[{cid}]"))
        criteria.append(
            CriterionRow(
                criterion_id=cid,
                name=str(item.get("name", cid)),
                weight=_dec(item.get("weight", 0)),
                skipped=False,
                grade=grade,
                contribution=_dec(item["contribution"])
                if item.get("contribution") is not None
                else None,
                title=item.get("title") or None,
                band=item.get("band") or None,
                out_of_band=str(item.get("out_of_band") or ""),
                evidence=item.get("evidence") or None,
                metric_ref=item.get("metric_ref") or None,
            )
        )
        # 항목별 등급·연속점수도 수치라 `analysis_metric_value` 로 간다(계약 3-1).
        values.append(
            MetricValueRow(
                metric_code=f"grade.{sport}.{motion}.{cid}",
                value=_dec(grade),
            )
        )
        stat = item.get("stat")
        if stat is not None:
            values.append(
                MetricValueRow(
                    metric_code=f"stat.{sport}.{motion}.{cid}",
                    value=_dec(stat),
                )
            )

    for item in result.get("skipped", []):
        cid = str(_require(item, "criterion_id", "skipped 항목"))
        criteria.append(
            CriterionRow(
                criterion_id=cid,
                name=str(item.get("name", cid)),
                weight=_dec(item.get("weight", 0)),  # 🔴 루브릭 원값 (재정규화 전)
                skipped=True,
            )
        )

    return ParsedReport(
        schema_version=schema_version,
        pipeline_version=str(
            result.get("pipeline_version") or env.get("code_version") or "unknown"
        ),
        rubric_sport=sport,
        rubric_motion=motion,
        rubric_version=rubric_version,
        summary=summary,
        model_name=model_name[:80],
        provisional=(
            bool(result["provisional"])
            if result.get("provisional") is not None
            else None
        ),
        previews=env.get("previews") or None,
        keypoint_quality=env.get("keypoint_quality") or None,
        metric_values=values,
        criteria=criteria,
    )
