"""회원 목록(관리자) 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.list_users_use_case import ListUsersUseCase
from app.user.application.use_cases.list_users_interactor import ListUsersInteractor
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_list_users_use_case(repository: UserRepositoryDep) -> ListUsersUseCase:
    return ListUsersInteractor(repository)


ListUsersUseCaseDep = Annotated[ListUsersUseCase, Depends(get_list_users_use_case)]
