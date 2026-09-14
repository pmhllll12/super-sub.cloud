"""`ReportReadPort` 의 PostgreSQL 구현. 미결 `jin` 27번 · `paik` 7번 · `ho` 28번.

`video` → `analysis_job` → `analysis_metric` → `analysis_report` 를 한 번에
조인해 한 행을 얻고, 항목·장면은 `analysis_metric_id` 로 따로 읽는다.
재분석이 있으면 `analysis_metric.created_at` 최신을 쓴다(적재가 앞의 것을
덮으므로 실제로는 한 벌이지만).

총점(`total_score`)·항목별 `stat` 은 `analysis_metric_value` 에 일반 지표와
같이 들어 있어 따로 조회한다(`ho` 28번). `stat` 코드는 그 작업의 루브릭
(`sport`/`motion`)이 있어야 조립되므로 옛 행(둘 다 NULL)은 전부 None.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.analysis_metric_criterion_orm import (
    AnalysisMetricCriterionOrm,
)
from app.analysis.adapter.outbound.orm.analysis_metric_orm import AnalysisMetricOrm
from app.analysis.adapter.outbound.orm.analysis_metric_value_orm import (
    AnalysisMetricValueOrm,
)
from app.analysis.adapter.outbound.orm.analysis_report_orm import AnalysisReportOrm
from app.analysis.adapter.outbound.orm.metric_definition_orm import (
    MetricDefinitionOrm,
)
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.application.dtos.report_view_dto import (
    ReportCriterionView,
    ReportSceneView,
    ReportView,
)
from app.analysis.application.ports.output.report_read_port import ReportReadPort

# 「이렇게 본 장면」의 시각 — 프레임 지표의 초 환산. `report_parser` 가
# `frame_metrics_seconds` 를 이 코드로 적재했다.
_SCENE_CODES = ("impact_frame", "follow_through_duration_frames")

# 총점 코드. `report_parser._TOTAL_SCORE_CODE` 와 같은 값이어야 한다(`ho` 28번).
_TOTAL_SCORE_CODE = "total_score"


class ReportReadPgRepository(ReportReadPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_for_video(self, video_id: UUID, user_id: UUID) -> ReportView | None:
        head = self._session.execute(
            select(
                AnalysisMetricOrm.id,
                AnalysisMetricOrm.created_at,
                AnalysisMetricOrm.rubric_sport,
                AnalysisMetricOrm.rubric_motion,
                AnalysisReportOrm.summary,
                AnalysisReportOrm.provisional,
                AnalysisReportOrm.overall_grade,
                AnalysisReportOrm.previews,
                AnalysisReportOrm.keypoint_quality,
            )
            .select_from(VideoOrm)
            .join(AnalysisJobOrm, AnalysisJobOrm.video_id == VideoOrm.id)
            .join(
                AnalysisMetricOrm,
                AnalysisMetricOrm.analysis_job_id == AnalysisJobOrm.id,
            )
            .join(
                AnalysisReportOrm,
                AnalysisReportOrm.analysis_metric_id == AnalysisMetricOrm.id,
            )
            .where(VideoOrm.id == video_id, VideoOrm.user_id == user_id)
            .order_by(AnalysisMetricOrm.created_at.desc())
            .limit(1)
        ).first()
        if head is None:
            return None

        metric_id = head.id
        sport = head.rubric_sport
        motion = head.rubric_motion

        criterion_rows = list(
            self._session.execute(
                select(AnalysisMetricCriterionOrm)
                .where(AnalysisMetricCriterionOrm.analysis_metric_id == metric_id)
                .order_by(
                    AnalysisMetricCriterionOrm.skipped,
                    AnalysisMetricCriterionOrm.criterion_id,
                )
            )
            .scalars()
        )

        # `stat.{sport}.{motion}.{criterion_id}` — 루브릭 정보가 없는 옛 행이면
        # (`sport`/`motion` NULL) 아예 안 찾는다. 정확한 코드 목록으로 `.in_()`
        # 하므로 두 문자열에 `_`가 있어도(예: `jump_shot`) LIKE 와일드카드 문제가
        # 없다.
        stat_codes = (
            {
                f"stat.{sport}.{motion}.{c.criterion_id}"
                for c in criterion_rows
                if not c.skipped
            }
            if sport and motion
            else set()
        )
        # 🔴 `dict(session.execute(...))` 로 쓰지 않는다 — `Result` 에 `keys()`
        # 가 있어서 `dict()` 가 매핑으로 오인하고 `result[key]` 를 시도해
        # `TypeError: not subscriptable` 로 죽는다. 컴프리헨션으로 짝을 만든다.
        extra_values = {
            code: value
            for code, value in self._session.execute(
                select(
                    AnalysisMetricValueOrm.metric_code,
                    AnalysisMetricValueOrm.value,
                ).where(
                    AnalysisMetricValueOrm.analysis_metric_id == metric_id,
                    AnalysisMetricValueOrm.metric_code.in_(
                        stat_codes | {_TOTAL_SCORE_CODE}
                    ),
                )
            )
        }
        total_score = extra_values.get(_TOTAL_SCORE_CODE)

        criteria = [
            ReportCriterionView(
                criterion_id=c.criterion_id,
                name=c.name,
                grade=c.grade,
                title=c.title,
                evidence=c.evidence,
                metric_ref=c.metric_ref,
                skipped=c.skipped,
                stat=(
                    float(extra_values[f"stat.{sport}.{motion}.{c.criterion_id}"])
                    if f"stat.{sport}.{motion}.{c.criterion_id}" in extra_values
                    else None
                ),
            )
            for c in criterion_rows
        ]

        scenes = [
            ReportSceneView(
                metric_code=code,
                label=label or code,
                at_seconds=float(value),
            )
            for code, value, label in self._session.execute(
                select(
                    AnalysisMetricValueOrm.metric_code,
                    AnalysisMetricValueOrm.value,
                    MetricDefinitionOrm.label,
                )
                .outerjoin(
                    MetricDefinitionOrm,
                    MetricDefinitionOrm.code == AnalysisMetricValueOrm.metric_code,
                )
                .where(
                    AnalysisMetricValueOrm.analysis_metric_id == metric_id,
                    AnalysisMetricValueOrm.metric_code.in_(_SCENE_CODES),
                )
            )
        ]

        return ReportView(
            video_id=video_id,
            analyzed_at=head.created_at,
            summary=head.summary,
            provisional=head.provisional,
            total_score=float(total_score) if total_score is not None else None,
            overall_grade=head.overall_grade,
            breakdown=criteria,
            scenes=scenes,
            previews=head.previews,
            keypoint_quality=head.keypoint_quality,
        )
