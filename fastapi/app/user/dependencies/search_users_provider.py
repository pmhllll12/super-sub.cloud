"""지인 검색 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.user_contact_use_cases import SearchUsersUseCase
from app.user.application.use_cases.user_contact_interactors import (
    SearchUsersInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_search_users_use_case(repository: UserRepositoryDep) -> SearchUsersUseCase:
    return SearchUsersInteractor(repository)


SearchUsersUseCaseDep = Annotated[
    SearchUsersUseCase, Depends(get_search_users_use_case)
]
