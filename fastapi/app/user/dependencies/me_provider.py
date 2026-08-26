"""내 정보 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.me_use_case import MeUseCase
from app.user.application.use_cases.me_interactor import MeInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_me_use_case(repository: UserRepositoryDep) -> MeUseCase:
    return MeInteractor(repository)


MeUseCaseDep = Annotated[MeUseCase, Depends(get_me_use_case)]
