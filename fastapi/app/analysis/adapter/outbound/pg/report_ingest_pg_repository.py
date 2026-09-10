"""`ReportIngestPort` 의 PostgreSQL 구현. 미결 `jin` 27번.

한 작업의 적재를 **통째로 바꾼다** — 재분석이 앞의 것을 덮기 때문이다
(`report.json` 에 타임스탬프가 없어 "언제 낸 것인가"는 `analyzed_at` 이 답한다).
지운 뒤 넣는 사이에 다른 트랜잭션이 끼어들지 않게 한 트랜잭션에서 한다.

🔴 **지표 코드는 넣기 전에 검사한다.** `metric_definition` 외래키가 잡아 주긴
하지만, flush 중간에 IntegrityError 가 나면 세션이 오염돼 이후 처리가 꼬인다.
미리 대조해서 통째로 거부한다(계약 3-1 `UNKNOWN_METRIC_CODE`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select
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
from app.analysis.application.ports.output.report_ingest_port import (
    ReportIngestPort,
    UnknownMetricCode,
)
from app.analysis.application.use_cases.report_parser import ParsedReport


class ReportIngestPgRepository(ReportIngestPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_job(self, job_id: UUID, parsed: ParsedReport) -> bool:
        job_exists = self._session.execute(
            select(AnalysisJobOrm.id).where(AnalysisJobOrm.id == job_id)
        ).first()
        if job_exists is None:
            return False

        codes = {row.metric_code for row in parsed.metric_values}
        known = set(
            self._session.execute(
                select(MetricDefinitionOrm.code).where(
                    MetricDefinitionOrm.code.in_(codes)
                )
            ).scalars()
        )
        missing = sorted(codes - known)
        if missing:
            raise UnknownMetricCode(
                "`metric_definition` 에 없는 지표 코드: " + ", ".join(missing[:10])
            )

        now = datetime.now(timezone.utc)

        # 재분석은 앞의 것을 덮는다 — CASCADE 가 value·criterion·report 를 함께 지운다.
        self._session.execute(
            delete(AnalysisMetricOrm).where(
                AnalysisMetricOrm.analysis_job_id == job_id
            )
        )
        self._session.flush()

        metric_id = uuid4()
        self._session.add(
            AnalysisMetricOrm(
                id=metric_id,
                analysis_job_id=job_id,
                pipeline_version=parsed.pipeline_version[:40],
                rubric_sport=parsed.rubric_sport[:20],
                rubric_motion=parsed.rubric_motion[:30],
                rubric_version=parsed.rubric_version[:20],
                created_at=now,
            )
        )
        self._session.flush()

        self._session.add_all(
            AnalysisMetricValueOrm(
                id=uuid4(),
                analysis_metric_id=metric_id,
                metric_code=v.metric_code,
                value=v.value,
                frame_index=v.frame_index,
            )
            for v in parsed.metric_values
        )
        self._session.add_all(
            AnalysisMetricCriterionOrm(
                id=uuid4(),
                analysis_metric_id=metric_id,
                criterion_id=c.criterion_id[:50],
                name=c.name[:80],
                grade=c.grade,
                weight=c.weight,
                contribution=c.contribution,
                title=c.title[:80] if c.title else None,
                band=c.band[:60] if c.band else None,
                out_of_band=c.out_of_band[:40],
                evidence=c.evidence,
                metric_ref=c.metric_ref[:50] if c.metric_ref else None,
                skipped=c.skipped,
            )
            for c in parsed.criteria
        )
        self._session.add(
            AnalysisReportOrm(
                id=uuid4(),
                analysis_metric_id=metric_id,
                summary=parsed.summary,
                model_name=parsed.model_name[:80],
                schema_version=parsed.schema_version[:10],
                provisional=parsed.provisional,
                previews=parsed.previews,
                keypoint_quality=parsed.keypoint_quality,
                created_at=now,
            )
        )
        self._session.commit()
        return True
