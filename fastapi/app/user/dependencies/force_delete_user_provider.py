"""회원 강제 탈퇴(관리자) 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.force_delete_user_use_case import (
    ForceDeleteUserUseCase,
)
from app.user.application.use_cases.force_delete_user_interactor import (
    ForceDeleteUserInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_force_delete_user_use_case(
    repository: UserRepositoryDep,
) -> ForceDeleteUserUseCase:
    return ForceDeleteUserInteractor(repository)


ForceDeleteUserUseCaseDep = Annotated[
    ForceDeleteUserUseCase, Depends(get_force_delete_user_use_case)
]
