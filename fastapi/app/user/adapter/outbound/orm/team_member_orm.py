"""`team_member` 테이블. 부록 D 도메인 ①.

**탈퇴해도 행을 지우지 않는다.** 경기·평가 이력이 이 행을 참조하므로 `left_at` 으로
소프트 삭제한다(부록 D.6 — 삭제 연쇄에 넣지 않는 이유). 재가입이 가능하므로
`joined_at` 을 함께 두고, 부록 D.7 의 유일 제약도 셋을 묶는다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamMemberOrm(Base):
    __tablename__ = "team_member"

    # 경기·평가 이력이 소속 구간을 참조하므로 대리키를 둔다
    # (부록 D 의 position 테이블과 같은 이유).
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # NULL 이면 현재 소속이다. 거르는 것은 도메인 규칙의 몫이라 여기서 판단하지 않는다.
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # 부록 D.7 — 재가입 이력을 남기면서 중복 소속을 막는다.
        UniqueConstraint(
            "team_id", "user_id", "joined_at", name="uq_team_member_team_user_joined"
        ),
    )
