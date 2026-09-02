"""내 카드 생성 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.application.ports.input.create_my_card_use_case import (
    CreateMyCardUseCase,
)
from app.card.application.use_cases.create_my_card_interactor import (
    CreateMyCardInteractor,
)
from app.card.dependencies.card_repository_provider import CardRepositoryDep


def get_create_my_card_use_case(repository: CardRepositoryDep) -> CreateMyCardUseCase:
    return CreateMyCardInteractor(repository)


CreateMyCardUseCaseDep = Annotated[
    CreateMyCardUseCase, Depends(get_create_my_card_use_case)
]
