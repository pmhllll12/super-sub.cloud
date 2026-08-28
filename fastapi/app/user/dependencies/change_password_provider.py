"""비밀번호 변경 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.change_password_use_case import (
    ChangePasswordUseCase,
)
from app.user.application.use_cases.change_password_interactor import (
    ChangePasswordInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_change_password_use_case(
    repository: UserRepositoryDep,
) -> ChangePasswordUseCase:
    return ChangePasswordInteractor(repository)


ChangePasswordUseCaseDep = Annotated[
    ChangePasswordUseCase, Depends(get_change_password_use_case)
]
