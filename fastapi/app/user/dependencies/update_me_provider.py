"""내 정보 수정 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.update_me_use_case import UpdateMeUseCase
from app.user.application.use_cases.update_me_interactor import UpdateMeInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_update_me_use_case(repository: UserRepositoryDep) -> UpdateMeUseCase:
    return UpdateMeInteractor(repository)


UpdateMeUseCaseDep = Annotated[UpdateMeUseCase, Depends(get_update_me_use_case)]
