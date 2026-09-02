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
    CreateTeamUseCase,
    JoinTeamUseCase,
    LeaveTeamUseCase,
    ReadTeamUseCase,
)
from app.user.application.ports.output.team_port import TeamPort
from app.user.application.use_cases.team_interactors import (
    CreateTeamInteractor,
    JoinTeamInteractor,
    LeaveTeamInteractor,
    ReadTeamInteractor,
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
