"""지인 신청 수락 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.user_contact_use_cases import (
    AcceptContactUseCase,
)
from app.user.application.use_cases.user_contact_interactors import (
    AcceptContactInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_accept_contact_use_case(
    repository: UserRepositoryDep,
) -> AcceptContactUseCase:
    return AcceptContactInteractor(repository)


AcceptContactUseCaseDep = Annotated[
    AcceptContactUseCase, Depends(get_accept_contact_use_case)
]
