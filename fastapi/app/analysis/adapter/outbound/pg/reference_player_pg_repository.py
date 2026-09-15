"""`ReferencePlayerPort`의 PostgreSQL 구현. `paik` 29번."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.reference_player_orm import (
    ReferencePlayerOrm,
)
from app.analysis.application.ports.output.reference_player_port import (
    ReferencePlayerPort,
)
from app.analysis.domain.entities.reference_player_entity import (
    ReferencePlayerEntity,
)


def _to_entity(row: ReferencePlayerOrm) -> ReferencePlayerEntity:
    return ReferencePlayerEntity(id=row.id, name=row.name, report_key=row.report_key)


class ReferencePlayerPgRepository(ReferencePlayerPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_players(self) -> list[ReferencePlayerEntity]:
        rows = self._session.execute(select(ReferencePlayerOrm)).scalars().all()
        return [_to_entity(r) for r in rows]

    def find_player(self, player_id: str) -> ReferencePlayerEntity | None:
        row = self._session.get(ReferencePlayerOrm, player_id)
        return _to_entity(row) if row is not None else None
