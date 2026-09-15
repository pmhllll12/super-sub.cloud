"""경기 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.match.adapter.outbound.pg.match_pg_repository import MatchPgRepository
from app.match.application.ports.input.match_use_cases import (
    AcceptApplicationUseCase,
    AcceptTeamMatchRequestUseCase,
    ApplyToMatchUseCase,
    CancelMatchUseCase,
    CancelTeamMatchRequestUseCase,
    CreateMatchUseCase,
    CreateTeamMatchRequestUseCase,
    ListApplicationsUseCase,
    ListTeamMatchesUseCase,
    ListTeamMatchRequestsUseCase,
    ReadMatchUseCase,
    RejectTeamMatchRequestUseCase,
    RemoveApplicationUseCase,
    SearchMatchesUseCase,
    UpdateMatchUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.application_interactors import (
    AcceptApplicationInteractor,
    ApplyToMatchInteractor,
    ListApplicationsInteractor,
    RemoveApplicationInteractor,
)
from app.match.application.use_cases.match_interactors import (
    CancelMatchInteractor,
    CreateMatchInteractor,
    ListTeamMatchesInteractor,
    ReadMatchInteractor,
    SearchMatchesInteractor,
    UpdateMatchInteractor,
)
from app.match.application.use_cases.team_match_request_interactors import (
    AcceptTeamMatchRequestInteractor,
    CancelTeamMatchRequestInteractor,
    CreateTeamMatchRequestInteractor,
    ListTeamMatchRequestsInteractor,
    RejectTeamMatchRequestInteractor,
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


def get_update_match_use_case(repository: MatchRepositoryDep) -> UpdateMatchUseCase:
    return UpdateMatchInteractor(repository)


def get_cancel_match_use_case(repository: MatchRepositoryDep) -> CancelMatchUseCase:
    return CancelMatchInteractor(repository)


UpdateMatchUseCaseDep = Annotated[
    UpdateMatchUseCase, Depends(get_update_match_use_case)
]
CancelMatchUseCaseDep = Annotated[
    CancelMatchUseCase, Depends(get_cancel_match_use_case)
]


def get_search_matches_use_case(
    repository: MatchRepositoryDep,
) -> SearchMatchesUseCase:
    return SearchMatchesInteractor(repository)


SearchMatchesUseCaseDep = Annotated[
    SearchMatchesUseCase, Depends(get_search_matches_use_case)
]


CreateMatchUseCaseDep = Annotated[
    CreateMatchUseCase, Depends(get_create_match_use_case)
]
ReadMatchUseCaseDep = Annotated[ReadMatchUseCase, Depends(get_read_match_use_case)]


def get_apply_use_case(repository: MatchRepositoryDep) -> ApplyToMatchUseCase:
    return ApplyToMatchInteractor(repository)


def get_accept_use_case(repository: MatchRepositoryDep) -> AcceptApplicationUseCase:
    return AcceptApplicationInteractor(repository)


def get_remove_application_use_case(
    repository: MatchRepositoryDep,
) -> RemoveApplicationUseCase:
    return RemoveApplicationInteractor(repository)


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
RemoveApplicationUseCaseDep = Annotated[
    RemoveApplicationUseCase, Depends(get_remove_application_use_case)
]


def get_create_team_match_request_use_case(
    repository: MatchRepositoryDep,
) -> CreateTeamMatchRequestUseCase:
    return CreateTeamMatchRequestInteractor(repository)


def get_list_team_match_requests_use_case(
    repository: MatchRepositoryDep,
) -> ListTeamMatchRequestsUseCase:
    return ListTeamMatchRequestsInteractor(repository)


def get_accept_team_match_request_use_case(
    repository: MatchRepositoryDep,
) -> AcceptTeamMatchRequestUseCase:
    return AcceptTeamMatchRequestInteractor(repository)


def get_reject_team_match_request_use_case(
    repository: MatchRepositoryDep,
) -> RejectTeamMatchRequestUseCase:
    return RejectTeamMatchRequestInteractor(repository)


def get_cancel_team_match_request_use_case(
    repository: MatchRepositoryDep,
) -> CancelTeamMatchRequestUseCase:
    return CancelTeamMatchRequestInteractor(repository)


CreateTeamMatchRequestUseCaseDep = Annotated[
    CreateTeamMatchRequestUseCase, Depends(get_create_team_match_request_use_case)
]
ListTeamMatchRequestsUseCaseDep = Annotated[
    ListTeamMatchRequestsUseCase, Depends(get_list_team_match_requests_use_case)
]
AcceptTeamMatchRequestUseCaseDep = Annotated[
    AcceptTeamMatchRequestUseCase, Depends(get_accept_team_match_request_use_case)
]
RejectTeamMatchRequestUseCaseDep = Annotated[
    RejectTeamMatchRequestUseCase, Depends(get_reject_team_match_request_use_case)
]
CancelTeamMatchRequestUseCaseDep = Annotated[
    CancelTeamMatchRequestUseCase, Depends(get_cancel_team_match_request_use_case)
]

