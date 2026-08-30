"""`metric_definition` 테이블. 부록 D 도메인 ②.

지표 항목 1개의 정의다(예: 임팩트 시 무릎 각도).

**지표를 컬럼으로 고정하지 않는 이유**는 종목·동작마다 항목이 다르기 때문이다
(부록 D.4). 항목을 데이터로 두면 종목을 열 때 마이그레이션이 필요 없다.

기본키를 `code` 로 둔 것은 같은 도메인의 `title_definition` 과 맞춘 것이다.
값 테이블(`analysis_metric_value`)이 코드로 참조하므로 대리키를 두면 조회마다
한 단계가 더 붙는다.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MetricDefinitionOrm(Base):
    __tablename__ = "metric_definition"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    # 단위(deg · deg/s · m 등). 단위 없이 숫자만 남기면 나중에 해석이 갈린다.
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    # 부록 D.3 이 sport 를 가리키는 외래키로 정의하지만 그 테이블이 아직 없다.
    sport_code: Mapped[str] = mapped_column(String(20), nullable=False)
