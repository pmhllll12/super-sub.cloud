"""`member_match_position` 테이블. 부록 D 도메인 ④. `paik` 18번(개인 조건).

내가 뛸 수 있는 포지션 — 여러 개. 팀 조건에는 없다(포지션은 "내가 어디서
뛰는가"라 개인 값이다 — 팀은 지역·시간만 갖는다).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemberMatchPositionOrm(Base):
    __tablename__ = "member_match_position"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    position_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("position.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "position_id", name="uq_member_match_position"
        ),
    )
