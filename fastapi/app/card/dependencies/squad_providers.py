"""스쿼드 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.card.adapter.outbound.pg.squad_pg_repository import SquadPgRepository
from app.card.application.ports.input.squad_use_cases import (
    CreateSquadUseCase,
    DischargeMemberUseCase,
    EnlistCardUseCase,
    PublicSquadUseCase,
    TeamSquadUseCase,
)
from app.card.application.ports.output.squad_port import SquadPort
from app.card.application.use_cases.squad_interactors import (
    CreateSquadInteractor,
    DischargeMemberInteractor,
    EnlistCardInteractor,
    PublicSquadInteractor,
    TeamSquadInteractor,
)
from app.core.database import get_session


def get_squad_repository(
    session: Annotated[Session, Depends(get_session)],
) -> SquadPort:
    return SquadPgRepository(session)


SquadRepositoryDep = Annotated[SquadPort, Depends(get_squad_repository)]


def get_create_squad_use_case(repository: SquadRepositoryDep) -> CreateSquadUseCase:
    return CreateSquadInteractor(repository)


def get_team_squad_use_case(repository: SquadRepositoryDep) -> TeamSquadUseCase:
    return TeamSquadInteractor(repository)


def get_public_squad_use_case(repository: SquadRepositoryDep) -> PublicSquadUseCase:
    return PublicSquadInteractor(repository)


def get_enlist_card_use_case(repository: SquadRepositoryDep) -> EnlistCardUseCase:
    return EnlistCardInteractor(repository)


def get_discharge_member_use_case(
    repository: SquadRepositoryDep,
) -> DischargeMemberUseCase:
    return DischargeMemberInteractor(repository)


CreateSquadUseCaseDep = Annotated[
    CreateSquadUseCase, Depends(get_create_squad_use_case)
]
TeamSquadUseCaseDep = Annotated[TeamSquadUseCase, Depends(get_team_squad_use_case)]
PublicSquadUseCaseDep = Annotated[
    PublicSquadUseCase, Depends(get_public_squad_use_case)
]
EnlistCardUseCaseDep = Annotated[EnlistCardUseCase, Depends(get_enlist_card_use_case)]
DischargeMemberUseCaseDep = Annotated[
    DischargeMemberUseCase, Depends(get_discharge_member_use_case)
]
