"""경기 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.match.adapter.outbound.pg.match_pg_repository import MatchPgRepository
from app.match.application.ports.input.match_use_cases import (
    CreateMatchUseCase,
    ReadMatchUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.match_interactors import (
    CreateMatchInteractor,
    ReadMatchInteractor,
)


def get_match_repository(
    session: Annotated[Session, Depends(get_session)],
) -> MatchPort:
    return MatchPgRepository(session)


MatchRepositoryDep = Annotated[MatchPort, Depends(get_match_repository)]


def get_create_match_use_case(repository: MatchRepositoryDep) -> CreateMatchUseCase:
    return CreateMatchInteractor(repository)


def get_read_match_use_case(repository: MatchRepositoryDep) -> ReadMatchUseCase:
    return ReadMatchInteractor(repository)


CreateMatchUseCaseDep = Annotated[
    CreateMatchUseCase, Depends(get_create_match_use_case)
]
ReadMatchUseCaseDep = Annotated[ReadMatchUseCase, Depends(get_read_match_use_case)]
