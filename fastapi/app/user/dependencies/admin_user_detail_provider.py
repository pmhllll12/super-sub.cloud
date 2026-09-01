"""회원 상세(관리자) 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.admin_user_detail_use_case import (
    AdminUserDetailUseCase,
)
from app.user.application.use_cases.admin_user_detail_interactor import (
    AdminUserDetailInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_admin_user_detail_use_case(
    repository: UserRepositoryDep,
) -> AdminUserDetailUseCase:
    return AdminUserDetailInteractor(repository)


AdminUserDetailUseCaseDep = Annotated[
    AdminUserDetailUseCase, Depends(get_admin_user_detail_use_case)
]
