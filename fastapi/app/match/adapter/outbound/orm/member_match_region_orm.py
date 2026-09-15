"""`member_match_region` 테이블. 부록 D 도메인 ④. `paik` 18번(개인 조건).

`user`(팀원)가 뛰고 싶은 지역 — 여러 개. `team_match_region`과 같은 모양이지만
**팀 조건과 절대 합치지 않는다**(`paik` 18번 「하지 말 것」 — 「우리 팀이 찾는
경기」와 「내가 뛸 수 있는 때」가 섞이면 안 된다. 같은 사람이 팀장이면서
팀원일 수 있어서다).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemberMatchRegionOrm(Base):
    __tablename__ = "member_match_region"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("region.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "region_id", name="uq_member_match_region"),
    )
