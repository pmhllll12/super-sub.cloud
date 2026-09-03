"""`match_position_need` 테이블. 부록 D 도메인 ④.

**포지션을 문자열 한 컬럼으로 두지 않는다**(부록 D.5) — 경기에 필요한 포지션이 둘
이상일 수 있어 행으로 나눈다. 인원은 포지션마다 다르므로 같은 행에 담는다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchPositionNeedOrm(Base):
    __tablename__ = "match_position_need"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    match_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("match.id"), nullable=False
    )
    # `position` 은 `user` 컨텍스트의 테이블이다. 대리키를 참조한다 — 포지션 약칭은
    # 종목 안에서만 유일해서(`uq_position_sport_code`) 코드로는 가리킬 수 없다.
    position_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("position.id"), nullable=False
    )
    head_count: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        # 부록 D.7 — 경기당 포지션 1행. 같은 포지션을 두 줄로 적으면 인원이 갈린다.
        UniqueConstraint("match_id", "position_id", name="uq_match_position_need"),
    )
