"""`team_match_region` 테이블. 부록 D 도메인 ④. `paik` 18번(팀 조건).

팀이 경기하고 싶은 지역 — **여러 개**라 행으로 나눈다(제1정규형, `match_position_need`
와 같은 판단). `team`은 `user` 컨텍스트, `region`은 `user` 컨텍스트지만 둘 다
**문자열 FK로만** 참조한다(임포트 금지).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamMatchRegionOrm(Base):
    __tablename__ = "team_match_region"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("region.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("team_id", "region_id", name="uq_team_match_region"),
    )
