"""`member_match_slot` 테이블. 부록 D 도메인 ④. `paik` 18번(개인 조건).

`team_match_slot`과 같은 모양, 대상만 `user`. 합치지 않는 이유는
`member_match_region` docstring 참고.
"""

from __future__ import annotations

from datetime import time
from uuid import UUID

from sqlalchemy import ForeignKey, SmallInteger, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemberMatchSlotOrm(Base):
    __tablename__ = "member_match_slot"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
