"""지인 목록·수신 신청 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.user.application.ports.input.user_contact_use_cases import (
    ListContactRequestsUseCase,
    ListContactsUseCase,
)
from app.user.application.use_cases.user_contact_interactors import (
    ListContactRequestsInteractor,
    ListContactsInteractor,
)
from app.user.dependencies.user_repository_provider import UserRepositoryDep


def get_list_contacts_use_case(repository: UserRepositoryDep) -> ListContactsUseCase:
    return ListContactsInteractor(repository)


def get_list_contact_requests_use_case(
    repository: UserRepositoryDep,
) -> ListContactRequestsUseCase:
    return ListContactRequestsInteractor(repository)


ListContactsUseCaseDep = Annotated[
    ListContactsUseCase, Depends(get_list_contacts_use_case)
]
ListContactRequestsUseCaseDep = Annotated[
    ListContactRequestsUseCase, Depends(get_list_contact_requests_use_case)
]
