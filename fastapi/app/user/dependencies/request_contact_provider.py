"""지인 신청 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.user_contact_use_cases import (
    RequestContactUseCase,
)
from app.user.application.use_cases.user_contact_interactors import (
    RequestContactInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_request_contact_use_case(
    repository: UserRepositoryDep,
) -> RequestContactUseCase:
    return RequestContactInteractor(repository)


RequestContactUseCaseDep = Annotated[
    RequestContactUseCase, Depends(get_request_contact_use_case)
]
