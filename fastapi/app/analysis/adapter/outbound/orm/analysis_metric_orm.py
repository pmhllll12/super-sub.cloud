"""`analysis_metric` 테이블. 부록 D 도메인 ② — QUA-002.

분석 실행 1회가 낸 **지표 묶음**이다. 값은 `analysis_metric_value` 에 항목당 한 행씩
들어간다.

🔴 **`pipeline_version` 이 이 테이블의 존재 이유다.** 채점 기준이 바뀌어도 과거 결과가
어느 버전으로 산출된 것인지 판별할 수 있어야 한다(QUA-002). 비워 두면 그 판별이
불가능해지므로 `nullable=False` 다.

부록 D.7 — 작업당 지표 집합 1건.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisMetricOrm(Base):
    __tablename__ = "analysis_metric"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_job.id"), nullable=False
    )
    pipeline_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 작업당 지표 집합 1건.
        UniqueConstraint("analysis_job_id", name="uq_analysis_metric_job"),
    )
