"""`review_selection` 테이블. 부록 D 도메인 ⑤ — 평가에서 고른 선택지.

🔴 **대리키(`id`)를 두지 않는다.** `(review_id, option_code)` 복합 기본키가 곧
"같은 평가에서 같은 선택지를 두 번 담을 수 없다"는 규칙이다 — 대리키를 두면 그
규칙이 사라진다. 부록 D 가 명시적으로 금지한 자리이고, 복합키를 쓰는 유일한
테이블이다(D "모든 테이블이 단일 컬럼 기본키를 쓴다. 복합키는 review_selection
하나뿐이며 비키 속성이 없다").
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReviewSelectionOrm(Base):
    __tablename__ = "review_selection"

    review_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("review.id"), primary_key=True
    )
    option_code: Mapped[str] = mapped_column(
        String(40), ForeignKey("review_option.code"), primary_key=True
    )
