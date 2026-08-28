"""전체 로그아웃 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.logout_all_use_case import LogoutAllUseCase
from app.user.application.use_cases.logout_all_interactor import LogoutAllInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_logout_all_use_case(repository: UserRepositoryDep) -> LogoutAllUseCase:
    return LogoutAllInteractor(repository)


LogoutAllUseCaseDep = Annotated[LogoutAllUseCase, Depends(get_logout_all_use_case)]
