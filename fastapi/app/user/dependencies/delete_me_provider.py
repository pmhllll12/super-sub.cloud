"""탈퇴 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.delete_me_use_case import DeleteMeUseCase
from app.user.application.use_cases.delete_me_interactor import DeleteMeInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_delete_me_use_case(repository: UserRepositoryDep) -> DeleteMeUseCase:
    return DeleteMeInteractor(repository)


DeleteMeUseCaseDep = Annotated[DeleteMeUseCase, Depends(get_delete_me_use_case)]
