"""카드·호칭 유스케이스."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol
from uuid import UUID

from app.cards.domain import Card, PublicCard, to_public, visible_titles
from app.errors import ApiError


class CardRepository(Protocol):
    """출력 포트. 구현은 `stub_repository.py`, 나중에 `pg_repository.py`."""

    def find_by_user(self, user_id: UUID) -> Card | None: ...

    def find_by_slug(self, public_slug: str) -> Card | None: ...


class CardService:
    def __init__(self, repository: CardRepository) -> None:
        self._repo = repository

    def my_card(self, user_id: UUID) -> Card:
        card = self._repo.find_by_user(user_id)
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")
        return self._with_visible_titles(card)

    def public_card(self, public_slug: str) -> PublicCard:
        card = self._repo.find_by_slug(public_slug)
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")
        return to_public(self._with_visible_titles(card))

    @staticmethod
    def _with_visible_titles(card: Card) -> Card:
        return replace(card, titles=visible_titles(card.titles))
