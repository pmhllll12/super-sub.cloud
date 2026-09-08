"""`coach_referral` 테이블. 부록 D 도메인 ⑥ — 레슨·코치 연결과 수수료.

🔴 **중복을 막는 유일 제약이 없다.** 같은 사람이 같은 코치에게 여러 번
연결을 요청할 수 있다 — 상담을 여러 번 받는 것이 자연스러운 흐름이라
`report`(신고)처럼 중복을 막지 않는 쪽을 택했다.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoachReferralOrm(Base):
    __tablename__ = "coach_referral"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("user.id"), nullable=False)
    coach_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("coach.id"), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
