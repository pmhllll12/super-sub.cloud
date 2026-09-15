"""`team_match_slot` 테이블. 부록 D 도메인 ④. `paik` 18번(팀 조건).

팀이 경기 가능한 요일·시각 — **여러 개**라 행으로 나눈다. `start_time <
end_time`은 애플리케이션(도메인 규칙)이 막는다 — 뒤집힌 시간은 겹침 계산에서
늘 거짓이라 DB만으로는 "조용히 아무것도 안 걸리는" 사고를 못 막는다(`paik`
18번이 명시한 요구).
"""

from __future__ import annotations

from datetime import time
from uuid import UUID

from sqlalchemy import ForeignKey, SmallInteger, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamMatchSlotOrm(Base):
    __tablename__ = "team_match_slot"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id", ondelete="CASCADE"), nullable=False
    )
    # 0=월 ~ 6=일 (파이썬 datetime.weekday()와 같은 축).
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
