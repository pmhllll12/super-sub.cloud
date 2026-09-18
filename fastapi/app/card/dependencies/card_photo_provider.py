"""카드 사진 업로드 유스케이스 프로바이더 (2026-09-18)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.application.ports.input.card_photo_use_case import CardPhotoUploadUseCase
from app.card.application.use_cases.card_photo_interactor import (
    CardPhotoUploadInteractor,
)
from app.card.dependencies.card_repository_provider import CardRepositoryDep
from app.card.dependencies.photo_storage_provider import CardPhotoStorageDep


def get_card_photo_upload_use_case(
    repository: CardRepositoryDep, photos: CardPhotoStorageDep
) -> CardPhotoUploadUseCase:
    """🔴 **여기는 `CardPhotoStorageDep`(503 갈래)다** — 올릴 자리를 못 내주면
    사진 기능 자체가 안 되는 것이라 조용히 넘어가면 안 된다. 카드를 *읽는*
    자리만 `Optional` 을 쓴다."""
    return CardPhotoUploadInteractor(repository, photos)


CardPhotoUploadUseCaseDep = Annotated[
    CardPhotoUploadUseCase, Depends(get_card_photo_upload_use_case)
]
