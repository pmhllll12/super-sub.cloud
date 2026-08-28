"""`analysis_report` 테이블. 부록 D 도메인 ② — SFR-003.

지표를 근거로 만든 요약 문장이다.

🔴 **지표와 테이블을 나눈 것이 요점이다.** 여기 들어가는 문장은 언어 모델 생성물이라
비결정적이고, 지표는 결정론적이다(QUA-001). 한 테이블에 섞으면 "다시 돌리면 달라지는
값"과 "언제나 같아야 하는 값"이 구별되지 않는다(부록 D.5).

**항목별 등급과 총점은 여기에 없다** — 그것은 수치라서 `analysis_metric_value` 로
간다(3장 4). 여기는 사람이 읽을 문장만 담는다.

부록 D.7 — 지표 집합당 요약 1건.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisReportOrm(Base):
    __tablename__ = "analysis_report"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    analysis_metric_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_metric.id"), nullable=False
    )
    # 선수에게 보여줄 코멘트. 두 문장 이내, 총점·등급 숫자를 넣지 않는다(3장 4).
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # 어느 모델이 썼는지. 모델을 바꾸면 문장 품질이 달라지므로 남긴다
    # (5장 CON-004 — 라이선스 문제로 교체될 수 있다).
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 지표 집합당 요약 1건.
        UniqueConstraint("analysis_metric_id", name="uq_analysis_report_metric"),
    )
