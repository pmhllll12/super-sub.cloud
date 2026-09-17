"""`RegionPort` 의 PostgreSQL 구현. `paik` 19번."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.user.adapter.outbound.orm.region_orm import RegionOrm
from app.user.application.ports.output.region_port import RegionPort
from app.user.domain.entities.region_entity import RegionEntity


class RegionPgRepository(RegionPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_regions(self) -> list[RegionEntity]:
        stmt = select(
            RegionOrm.id, RegionOrm.city, RegionOrm.district, RegionOrm.label
        ).order_by(RegionOrm.city, RegionOrm.district)
        return [
            RegionEntity(id=r[0], city=r[1], district=r[2], label=r[3])
            for r in self._session.execute(stmt).tuples().all()
        ]
