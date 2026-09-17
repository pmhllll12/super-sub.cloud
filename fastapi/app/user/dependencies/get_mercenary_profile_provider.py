"""내 용병 프로필 조회 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.get_mercenary_profile_use_case import (
    GetMercenaryProfileUseCase,
)
from app.user.application.use_cases.get_mercenary_profile_interactor import (
    GetMercenaryProfileInteractor,
)
from app.user.dependencies.mercenary_repository_provider import MercenaryRepositoryDep


def get_get_mercenary_profile_use_case(
    repository: MercenaryRepositoryDep,
) -> GetMercenaryProfileUseCase:
    return GetMercenaryProfileInteractor(repository)


GetMercenaryProfileUseCaseDep = Annotated[
    GetMercenaryProfileUseCase, Depends(get_get_mercenary_profile_use_case)
]
