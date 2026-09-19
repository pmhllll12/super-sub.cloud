"""입력 포트 — 카드 사진 올릴 자리."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.card.application.dtos.card_dto import (
    CardPhotoUploadCommand,
    CardPhotoUploadResult,
)


class CardPhotoUploadUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CardPhotoUploadCommand) -> CardPhotoUploadResult:
        """사진을 올릴 사전 서명 주소를 만든다. 카드가 없으면 404."""
