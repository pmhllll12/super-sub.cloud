"""공개 카드 인터랙터."""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import PublicCardQuery, PublicCardResult
from app.card.application.ports.input.public_card_use_case import PublicCardUseCase
from app.card.application.ports.output.card_port import CardPort
from app.card.application.ports.output.photo_storage_port import PhotoStoragePort
from app.card.application.use_cases.card_assembler import (
    photo_url_of,
    to_public_card_result,
)
from app.card.domain.rules.card_rules import to_public, visible_titles
from app.card.domain.value_objects.public_slug_vo import PublicSlug
from app.core.errors import ApiError


class PublicCardInteractor(PublicCardUseCase):
    def __init__(
        self, repository: CardPort, photos: PhotoStoragePort | None = None
    ) -> None:
        self._repository = repository
        self._photos = photos

    def __call__(self, query: PublicCardQuery) -> PublicCardResult:
        card = self._repository.find_by_slug(PublicSlug(query.public_slug))
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        card = replace(card, titles=visible_titles(card.titles))
        return to_public_card_result(
            to_public(card), photo_url_of(card.style, self._photos)
        )
