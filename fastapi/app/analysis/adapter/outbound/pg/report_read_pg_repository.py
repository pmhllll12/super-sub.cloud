"""`ReportReadPort` 의 PostgreSQL 구현. 미결 `jin` 27번 · `paik` 7번.

`video` → `analysis_job` → `analysis_metric` → `analysis_report` 를 한 번에
조인해 한 행을 얻고, 항목·장면은 `analysis_metric_id` 로 따로 읽는다.
재분석이 있으면 `analysis_metric.created_at` 최신을 쓴다(적재가 앞의 것을
덮으므로 실제로는 한 벌이지만).
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


class ReportReadPgRepository(ReportReadPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_for_video(self, video_id: UUID, user_id: UUID) -> ReportView | None:
        head = self._session.execute(
            select(
                AnalysisMetricOrm.id,
                AnalysisMetricOrm.created_at,
                AnalysisReportOrm.summary,
                AnalysisReportOrm.provisional,
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

        criteria = [
            ReportCriterionView(
                criterion_id=c.criterion_id,
                name=c.name,
                grade=c.grade,
                title=c.title,
                evidence=c.evidence,
                metric_ref=c.metric_ref,
                skipped=c.skipped,
            )
            for c in self._session.execute(
                select(AnalysisMetricCriterionOrm)
                .where(AnalysisMetricCriterionOrm.analysis_metric_id == metric_id)
                .order_by(
                    AnalysisMetricCriterionOrm.skipped,
                    AnalysisMetricCriterionOrm.criterion_id,
                )
            )
            .scalars()
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
            breakdown=criteria,
            scenes=scenes,
            previews=head.previews,
            keypoint_quality=head.keypoint_quality,
        )
