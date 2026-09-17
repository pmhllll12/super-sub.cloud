"""`PositionPort` 의 PostgreSQL 구현.

`sport`·`position` 은 둘 다 `user` 컨텍스트의 테이블이라 ORM 을 그대로 쓴다.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.user.adapter.outbound.orm.position_orm import PositionOrm
from app.user.adapter.outbound.orm.sport_orm import SportOrm
from app.user.application.ports.output.position_port import PositionPort
from app.user.domain.entities.position_entity import PositionEntity


class PositionPgRepository(PositionPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def sport_exists(self, sport_code: str) -> bool:
        return (
            self._session.execute(
                select(SportOrm.code).where(SportOrm.code == sport_code)
            ).first()
            is not None
        )

    def list_positions(self, sport_code: str | None) -> list[PositionEntity]:
        stmt = select(
            PositionOrm.sport_code, PositionOrm.code, PositionOrm.label
        ).order_by(PositionOrm.sport_code, PositionOrm.code)
        if sport_code is not None:
            stmt = stmt.where(PositionOrm.sport_code == sport_code)
        return [
            PositionEntity(sport_code=r[0], code=r[1], label=r[2])
            for r in self._session.execute(stmt).tuples().all()
        ]
