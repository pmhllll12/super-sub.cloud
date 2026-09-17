"""경기 조건·후보 저장소·유스케이스 프로바이더. `paik` 18·20·21번."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.match.adapter.outbound.pg.match_preference_pg_repository import (
    MatchPreferencePgRepository,
)
from app.match.application.ports.input.match_preference_use_cases import (
    GetMemberPreferenceUseCase,
    GetTeamPreferenceUseCase,
    ListMatchCandidatesUseCase,
    ListMemberPreferencesUseCase,
    ListSquadCandidatesUseCase,
    SetMemberPreferenceUseCase,
    SetTeamPreferenceUseCase,
)
from app.match.application.ports.output.match_preference_port import (
    MatchPreferencePort,
)
from app.match.application.use_cases.match_preference_interactors import (
    GetMemberPreferenceInteractor,
    GetTeamPreferenceInteractor,
    ListMatchCandidatesInteractor,
    ListMemberPreferencesInteractor,
    ListSquadCandidatesInteractor,
    SetMemberPreferenceInteractor,
    SetTeamPreferenceInteractor,
)


def get_match_preference_repository(
    session: Annotated[Session, Depends(get_session)],
) -> MatchPreferencePort:
    return MatchPreferencePgRepository(session)


MatchPreferenceRepositoryDep = Annotated[
    MatchPreferencePort, Depends(get_match_preference_repository)
]


def get_set_team_preference_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> SetTeamPreferenceUseCase:
    return SetTeamPreferenceInteractor(repository)


def get_get_team_preference_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> GetTeamPreferenceUseCase:
    return GetTeamPreferenceInteractor(repository)


def get_set_member_preference_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> SetMemberPreferenceUseCase:
    return SetMemberPreferenceInteractor(repository)


def get_get_member_preference_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> GetMemberPreferenceUseCase:
    return GetMemberPreferenceInteractor(repository)


def get_list_member_preferences_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> ListMemberPreferencesUseCase:
    return ListMemberPreferencesInteractor(repository)


def get_list_match_candidates_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> ListMatchCandidatesUseCase:
    return ListMatchCandidatesInteractor(repository)


def get_list_squad_candidates_use_case(
    repository: MatchPreferenceRepositoryDep,
) -> ListSquadCandidatesUseCase:
    return ListSquadCandidatesInteractor(repository)


SetTeamPreferenceUseCaseDep = Annotated[
    SetTeamPreferenceUseCase, Depends(get_set_team_preference_use_case)
]
GetTeamPreferenceUseCaseDep = Annotated[
    GetTeamPreferenceUseCase, Depends(get_get_team_preference_use_case)
]
SetMemberPreferenceUseCaseDep = Annotated[
    SetMemberPreferenceUseCase, Depends(get_set_member_preference_use_case)
]
GetMemberPreferenceUseCaseDep = Annotated[
    GetMemberPreferenceUseCase, Depends(get_get_member_preference_use_case)
]
ListMemberPreferencesUseCaseDep = Annotated[
    ListMemberPreferencesUseCase, Depends(get_list_member_preferences_use_case)
]
ListMatchCandidatesUseCaseDep = Annotated[
    ListMatchCandidatesUseCase, Depends(get_list_match_candidates_use_case)
]
ListSquadCandidatesUseCaseDep = Annotated[
    ListSquadCandidatesUseCase, Depends(get_list_squad_candidates_use_case)
]
