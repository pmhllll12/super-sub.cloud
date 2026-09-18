"""내 카드 지우기 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.application.ports.input.delete_my_card_use_case import (
    DeleteMyCardUseCase,
)
from app.card.application.use_cases.delete_my_card_interactor import (
    DeleteMyCardInteractor,
)
from app.card.dependencies.card_repository_provider import CardRepositoryDep


def get_delete_my_card_use_case(repository: CardRepositoryDep) -> DeleteMyCardUseCase:
    return DeleteMyCardInteractor(repository)


DeleteMyCardUseCaseDep = Annotated[
    DeleteMyCardUseCase, Depends(get_delete_my_card_use_case)
]
