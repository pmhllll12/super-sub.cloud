"""포지션 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.user.adapter.outbound.pg.position_pg_repository import (
    PositionPgRepository,
)
from app.user.application.ports.input.position_use_cases import (
    ListPositionsUseCase,
)
from app.user.application.ports.output.position_port import PositionPort
from app.user.application.use_cases.position_interactors import (
    ListPositionsInteractor,
)


def get_position_repository(
    session: Annotated[Session, Depends(get_session)],
) -> PositionPort:
    return PositionPgRepository(session)


PositionRepositoryDep = Annotated[PositionPort, Depends(get_position_repository)]


def get_list_positions_use_case(
    repository: PositionRepositoryDep,
) -> ListPositionsUseCase:
    return ListPositionsInteractor(repository)


ListPositionsUseCaseDep = Annotated[
    ListPositionsUseCase, Depends(get_list_positions_use_case)
]
