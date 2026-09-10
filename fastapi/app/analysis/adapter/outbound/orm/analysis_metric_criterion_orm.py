"""`analysis_metric_criterion` 테이블. 부록 D 도메인 ② — 미결 `jin` 27번.

리포트의 `result.breakdown[]` 항목 하나가 여기 한 행이다. `analysis_metric_value`
가 **수치**(항목별 등급·`stat`·측정값)를 담는다면, 여기는 그 항목의 **맥락** —
칭호·구간·근거 문장이다.

🔴 `evidence` 만 언어 모델(EXAONE) 산출이라 비결정적이다. 나머지(등급·칭호·구간·
기여도)는 결정론적 코드(`scoring.aggregate`)가 정한다. 재현성(QUA-001)이 걸린
값은 수치이고 그건 `analysis_metric_value` 에 따로 있으므로, 문장이 여기 섞여도
"다시 돌리면 달라지는 값"과 "언제나 같아야 하는 값"의 구분은 깨지지 않는다.

필드 목록의 정본은 `agent/contracts/report_schema.yaml` 의 `breakdown_item` 이다.
봉투의 `schema_version` 이 그 계약의 버전을 싣고, 적재는 모르는 major 를 거부한다.

`skipped=True` 행은 `result.skipped[]` 항목이다 — 촬영 조건으로 채점에서 빠졌다.
🔴 **0점이 아니라 제외다.** `grade`·`evidence` 가 NULL 인 것이 곧 그 뜻이다.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisMetricCriterionOrm(Base):
    __tablename__ = "analysis_metric_criterion"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    analysis_metric_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_metric.id", ondelete="CASCADE"), nullable=False
    )
    # 🔴 종목·동작 안에서만 유일하다 — `grade.{sport}.{motion}.{criterion_id}` 로
    #    합성한다(`jin` 23번). 여기에 FK 를 걸지 않는 이유가 이것이다.
    criterion_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 0/1/2. `skipped` 행은 NULL — 없음이 곧 「제외」다.
    grade: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # `breakdown` 은 재정규화된 가중치(판정된 항목 합 1.0), `skipped` 는 루브릭
    # 원값이다. 봉투가 준 값을 그대로 넣는다.
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    # 이 항목이 총점에 실제로 보탠 점수(0~100 축). `skipped` 는 NULL.
    contribution: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    # 등급별 칭호(「채찍이 된 다리」). 등급 맥락의 출처다. `skipped` 는 NULL.
    title: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # 그 등급의 수치 구간 텍스트. 둘로 갈릴 수 있어("135~150 또는 170~180")
    # 파싱하지 않는다. 🔴 임계값이 검수 전이라 선수 화면에 내지 않는다(미결 24번).
    band: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # 0등급이 **구간 위**에서 왔는가(미결 20번). 빈 문자열이면 아니다. 개발
    # 확인용이고 선수 화면용이 아니다.
    out_of_band: Mapped[str] = mapped_column(
        String(40), nullable=False, default=""
    )
    # EXAONE 이 쓴 근거 문장. 🔴 등급 표기가 없다(2026.09.07~) — 문장에서 등급을
    # 정규식으로 뽑으려 하지 말 것(미결 `ho` 23·24번).
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 그 항목이 근거로 삼은 지표 코드. 사람이 읽을 이름·단위는 `metric_definition`.
    metric_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    skipped: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    __table_args__ = (
        # 한 분석에서 같은 항목이 두 번 나올 수 없다.
        UniqueConstraint(
            "analysis_metric_id",
            "criterion_id",
            name="uq_metric_criterion_item",
        ),
    )
