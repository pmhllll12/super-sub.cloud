"""`analysis_metric_value` 테이블. 부록 D 도메인 ② — SFR-002.

지표 묶음 1개 안의 항목 1개 값이다. **총점과 등급도 여기에 항목으로 들어간다**
(3장 4) — 카드에 능력치 컬럼을 두지 않는 원칙과 짝이다. 수치는 이 테이블에만 있고
리포트 경로로만 나간다(부록 D.5).

🔴 값을 `Float` 이 아니라 `Numeric` 으로 둔다. QUA-001 의 확인 방법이 **"같은 영상을
두 번 분석해 값이 일치하는지"** 인데, 부동소수는 저장·복원 과정에서 마지막 자리가
어긋날 수 있어 그 비교가 흔들린다. 십진 고정소수는 넣은 값이 그대로 나온다.

부록 D.7 — 항목당 값 1건.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisMetricValueOrm(Base):
    __tablename__ = "analysis_metric_value"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    analysis_metric_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_metric.id"), nullable=False
    )
    # 정의에 없는 코드가 들어오면 여기서 막힌다 — 오타 하나가 조용히 새 지표가 되는
    # 것을 외래키로 방지한다.
    metric_code: Mapped[str] = mapped_column(
        String(50), ForeignKey("metric_definition.code"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    # 근거가 된 프레임. 판정 결과에 프레임 번호를 함께 남긴다(3장 3)·SFR-003).
    frame_index: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (
        # 부록 D.7 — 항목당 값 1건.
        UniqueConstraint(
            "analysis_metric_id", "metric_code", name="uq_metric_value_item"
        ),
    )
