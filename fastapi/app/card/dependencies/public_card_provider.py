"""공개 카드 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.application.ports.input.public_card_use_case import PublicCardUseCase
from app.card.application.use_cases.public_card_interactor import (
    PublicCardInteractor,
)
from app.card.dependencies.card_repository_provider import CardRepositoryDep


def get_public_card_use_case(repository: CardRepositoryDep) -> PublicCardUseCase:
    return PublicCardInteractor(repository)


PublicCardUseCaseDep = Annotated[
    PublicCardUseCase, Depends(get_public_card_use_case)
]
