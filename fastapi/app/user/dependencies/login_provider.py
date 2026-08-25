"""로그인 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.login_use_case import LoginUseCase
from app.user.application.use_cases.login_interactor import LoginInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_login_use_case(repository: UserRepositoryDep) -> LoginUseCase:
    return LoginInteractor(repository)


LoginUseCaseDep = Annotated[LoginUseCase, Depends(get_login_use_case)]
