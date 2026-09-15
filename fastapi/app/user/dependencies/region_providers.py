"""지역 저장소·유스케이스 프로바이더. `paik` 19번."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.user.adapter.outbound.pg.region_pg_repository import RegionPgRepository
from app.user.application.ports.input.region_use_cases import ListRegionsUseCase
from app.user.application.ports.output.region_port import RegionPort
from app.user.application.use_cases.region_interactors import ListRegionsInteractor


def get_region_repository(
    session: Annotated[Session, Depends(get_session)],
) -> RegionPort:
    return RegionPgRepository(session)


RegionRepositoryDep = Annotated[RegionPort, Depends(get_region_repository)]


def get_list_regions_use_case(
    repository: RegionRepositoryDep,
) -> ListRegionsUseCase:
    return ListRegionsInteractor(repository)


ListRegionsUseCaseDep = Annotated[
    ListRegionsUseCase, Depends(get_list_regions_use_case)
]
