"""`analysis_job` 테이블. 부록 D 도메인 ② — PER-001.

분석 실행 1회다. **업로드 응답이 분석 완료를 기다리지 않는다**는 요구를 이 테이블이
받는다 — 업로드 시각과 완료 시각이 따로 남아야 그것을 확인할 수 있다.

같은 영상을 다시 분석할 수 있으므로 `video_id` 에 유일 제약을 걸지 않는다
(부록 D.7 에도 없다). 재분석 이력이 남는 편이 맞다 — 파이프라인 버전이 바뀌면
같은 영상에서 다른 지표가 나오고, 그 비교가 QUA-002 의 목적이다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisJobOrm(Base):
    __tablename__ = "analysis_job"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    video_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )

    # queued · running · succeeded · failed. 값 목록을 DB 제약으로 걸지 않는 이유는
    # 단계가 늘어날 때 마이그레이션 없이 넣기 위해서다.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # 실패 사유. 성공하면 비어 있다. 남기지 않으면 왜 실패했는지 물어볼 데가 없다.
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 🔴 시각 셋이 따로 있는 것이 PER-001 의 확인 방법이다. 하나로 합치면
    #    "업로드 응답이 분석을 기다렸는지"를 판별할 수 없다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
