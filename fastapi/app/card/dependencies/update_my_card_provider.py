"""내 카드 수정 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.application.ports.input.update_my_card_use_case import (
    UpdateMyCardUseCase,
)
from app.card.application.use_cases.update_my_card_interactor import (
    UpdateMyCardInteractor,
)
from app.card.dependencies.card_repository_provider import CardRepositoryDep


def get_update_my_card_use_case(repository: CardRepositoryDep) -> UpdateMyCardUseCase:
    return UpdateMyCardInteractor(repository)


UpdateMyCardUseCaseDep = Annotated[
    UpdateMyCardUseCase, Depends(get_update_my_card_use_case)
]
