"""팀 저장소·유스케이스 프로바이더.

**이 컨텍스트에서 팀 구현을 고르는 유일한 곳이다.** 계약 테스트는
`dependency_overrides` 로 스텁을 끼운다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.user.adapter.outbound.pg.team_pg_repository import TeamPgRepository
from app.user.application.ports.input.team_use_cases import (
    AcceptTeamInvitationUseCase,
    CancelTeamInvitationUseCase,
    CreateTeamInvitationUseCase,
    CreateTeamUseCase,
    JoinTeamUseCase,
    LeaveTeamUseCase,
    ListMyTeamInvitationsUseCase,
    ListTeamInvitationsUseCase,
    ReadTeamUseCase,
    RejectTeamInvitationUseCase,
)
from app.user.application.ports.output.team_port import TeamPort
from app.user.application.use_cases.team_interactors import (
    AcceptTeamInvitationInteractor,
    CancelTeamInvitationInteractor,
    CreateTeamInteractor,
    CreateTeamInvitationInteractor,
    JoinTeamInteractor,
    LeaveTeamInteractor,
    ListMyTeamInvitationsInteractor,
    ListTeamInvitationsInteractor,
    ReadTeamInteractor,
    RejectTeamInvitationInteractor,
)


def get_team_repository(
    session: Annotated[Session, Depends(get_session)],
) -> TeamPort:
    return TeamPgRepository(session)


TeamRepositoryDep = Annotated[TeamPort, Depends(get_team_repository)]


def get_create_team_use_case(repository: TeamRepositoryDep) -> CreateTeamUseCase:
    return CreateTeamInteractor(repository)


def get_read_team_use_case(repository: TeamRepositoryDep) -> ReadTeamUseCase:
    return ReadTeamInteractor(repository)


def get_join_team_use_case(repository: TeamRepositoryDep) -> JoinTeamUseCase:
    return JoinTeamInteractor(repository)


def get_leave_team_use_case(repository: TeamRepositoryDep) -> LeaveTeamUseCase:
    return LeaveTeamInteractor(repository)


CreateTeamUseCaseDep = Annotated[CreateTeamUseCase, Depends(get_create_team_use_case)]
ReadTeamUseCaseDep = Annotated[ReadTeamUseCase, Depends(get_read_team_use_case)]
JoinTeamUseCaseDep = Annotated[JoinTeamUseCase, Depends(get_join_team_use_case)]
LeaveTeamUseCaseDep = Annotated[LeaveTeamUseCase, Depends(get_leave_team_use_case)]


def get_create_team_invitation_use_case(
    repository: TeamRepositoryDep,
) -> CreateTeamInvitationUseCase:
    return CreateTeamInvitationInteractor(repository)


def get_list_team_invitations_use_case(
    repository: TeamRepositoryDep,
) -> ListTeamInvitationsUseCase:
    return ListTeamInvitationsInteractor(repository)


def get_list_my_team_invitations_use_case(
    repository: TeamRepositoryDep,
) -> ListMyTeamInvitationsUseCase:
    return ListMyTeamInvitationsInteractor(repository)


def get_accept_team_invitation_use_case(
    repository: TeamRepositoryDep,
) -> AcceptTeamInvitationUseCase:
    # 🔴 새 가입 로직 없이 기존 JoinTeamInteractor(자기-가입)를 그대로 문다.
    return AcceptTeamInvitationInteractor(repository, JoinTeamInteractor(repository))


def get_reject_team_invitation_use_case(
    repository: TeamRepositoryDep,
) -> RejectTeamInvitationUseCase:
    return RejectTeamInvitationInteractor(repository)


def get_cancel_team_invitation_use_case(
    repository: TeamRepositoryDep,
) -> CancelTeamInvitationUseCase:
    return CancelTeamInvitationInteractor(repository)


CreateTeamInvitationUseCaseDep = Annotated[
    CreateTeamInvitationUseCase, Depends(get_create_team_invitation_use_case)
]
ListTeamInvitationsUseCaseDep = Annotated[
    ListTeamInvitationsUseCase, Depends(get_list_team_invitations_use_case)
]
ListMyTeamInvitationsUseCaseDep = Annotated[
    ListMyTeamInvitationsUseCase, Depends(get_list_my_team_invitations_use_case)
]
AcceptTeamInvitationUseCaseDep = Annotated[
    AcceptTeamInvitationUseCase, Depends(get_accept_team_invitation_use_case)
]
RejectTeamInvitationUseCaseDep = Annotated[
    RejectTeamInvitationUseCase, Depends(get_reject_team_invitation_use_case)
]
CancelTeamInvitationUseCaseDep = Annotated[
    CancelTeamInvitationUseCase, Depends(get_cancel_team_invitation_use_case)
]
