"""`analysis_report` 테이블. 부록 D 도메인 ② — SFR-003 · 미결 `jin` 27번.

분석 실행 1회의 **분석 단위 결과**다. 항목별 값(등급·`stat`·측정값)은
`analysis_metric_value`, 항목별 맥락(칭호·구간·근거)은 `analysis_metric_criterion`
이 담고, 여기는 그 위 — 요약 문장과 분석 전체에 걸리는 메타(검수 전 여부·미리보기·
키포인트 품질)다.

🔴 **지표와 문장을 나눈 것이 요점이다.** `summary` 는 등급이 정해지면 코드가
짓는 결정론적 문장이지만(`scoring.summarize`), 항목별 `evidence` 는 언어 모델
생성물이라 비결정적이라 `analysis_metric_criterion` 에 둔다. 재현성(QUA-001)이
걸린 수치는 `analysis_metric_value` 에 있다.

부록 D.7 — 지표 집합당 1건.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisReportOrm(Base):
    __tablename__ = "analysis_report"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    analysis_metric_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_metric.id", ondelete="CASCADE"), nullable=False
    )
    # 선수에게 보여줄 코멘트. 두 문장 이내, 총점·등급 숫자를 넣지 않는다(3장 4).
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # 어느 모델이 썼는지. 모델을 바꾸면 문장 품질이 달라지므로 남긴다
    # (5장 CON-004 — 라이선스 문제로 교체될 수 있다).
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)

    # --- 미결 jin 27번: 적재가 봉투에서 실어 오는 분석 단위 메타 ---------------
    # 봉투의 `schema_version`. 적재 시 모르는 major 는 거부하지만, 실린 값은
    # "어느 계약으로 적재됐나"를 사후에 판별하게 남긴다. 옛 행은 NULL.
    schema_version: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    # 검수 전 루브릭으로 낸 값인가. 🔴 True 면 확정 점수로 보여주지 않는다.
    provisional: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # 스켈레톤 미리보기 S3 URI(`impact`·`tracked`). 비어 있으면 렌더링만 실패한
    # 것이고 측정·판정은 유효하다.
    previews: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 계약 3장 4)의 「신뢰도」 자리(`jin` 27번 곁가지). 스윙 측 게이트 관절의
    # 유효 프레임 비율 등. 🔴 키포인트 신뢰도 평균이 아니다 — 「누구를 쟀는가」는
    # `subject`(별건)가 답한다. 정규화가 안 되는 입력은 `known: false` 다.
    keypoint_quality: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 지표 집합당 요약 1건.
        UniqueConstraint("analysis_metric_id", name="uq_analysis_report_metric"),
    )
