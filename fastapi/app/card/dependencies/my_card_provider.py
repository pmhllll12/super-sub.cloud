"""내 카드 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.application.ports.input.my_card_use_case import MyCardUseCase
from app.card.application.use_cases.my_card_interactor import MyCardInteractor
from app.card.dependencies.card_repository_provider import CardRepositoryDep
from app.card.dependencies.photo_storage_provider import CardPhotoStorageOptionalDep


def get_my_card_use_case(
    repository: CardRepositoryDep, photos: CardPhotoStorageOptionalDep
) -> MyCardUseCase:
    return MyCardInteractor(repository, photos)


MyCardUseCaseDep = Annotated[MyCardUseCase, Depends(get_my_card_use_case)]
