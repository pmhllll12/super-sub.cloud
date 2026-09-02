"""경기 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.match.adapter.outbound.pg.match_pg_repository import MatchPgRepository
from app.match.application.ports.input.match_use_cases import (
    AcceptApplicationUseCase,
    ApplyToMatchUseCase,
    CreateMatchUseCase,
    ListApplicationsUseCase,
    ListTeamMatchesUseCase,
    ReadMatchUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.application_interactors import (
    AcceptApplicationInteractor,
    ApplyToMatchInteractor,
    ListApplicationsInteractor,
)
from app.match.application.use_cases.match_interactors import (
    CreateMatchInteractor,
    ListTeamMatchesInteractor,
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


def get_apply_use_case(repository: MatchRepositoryDep) -> ApplyToMatchUseCase:
    return ApplyToMatchInteractor(repository)


def get_accept_use_case(repository: MatchRepositoryDep) -> AcceptApplicationUseCase:
    return AcceptApplicationInteractor(repository)


def get_list_applications_use_case(
    repository: MatchRepositoryDep,
) -> ListApplicationsUseCase:
    return ListApplicationsInteractor(repository)


def get_list_team_matches_use_case(
    repository: MatchRepositoryDep,
) -> ListTeamMatchesUseCase:
    return ListTeamMatchesInteractor(repository)


ListTeamMatchesUseCaseDep = Annotated[
    ListTeamMatchesUseCase, Depends(get_list_team_matches_use_case)
]
ApplyToMatchUseCaseDep = Annotated[ApplyToMatchUseCase, Depends(get_apply_use_case)]
AcceptApplicationUseCaseDep = Annotated[
    AcceptApplicationUseCase, Depends(get_accept_use_case)
]
ListApplicationsUseCaseDep = Annotated[
    ListApplicationsUseCase, Depends(get_list_applications_use_case)
]

