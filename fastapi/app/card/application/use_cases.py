"""카드 컨텍스트의 유스케이스."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from app.card.application.ports import CardRepository
from app.card.domain.entities import Card, PublicCard
from app.card.domain.rules import to_public, visible_titles
from app.card.domain.value_objects import PublicSlug
from app.errors import ApiError

def _not_found() -> ApiError:
    # 예외 인스턴스를 재사용하면 트레이스백이 누적된다. 매번 새로 만든다.
    return ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")


def _ordered(card: Card) -> Card:
    return replace(card, titles=visible_titles(card.titles))


class MyCardUseCase:
    def __init__(self, repository: CardRepository) -> None:
        self._repo = repository

    def __call__(self, user_id: UUID) -> Card:
        card = self._repo.find_by_owner(user_id)
        if card is None:
            raise _not_found()
        return _ordered(card)


class PublicCardUseCase:
    def __init__(self, repository: CardRepository) -> None:
        self._repo = repository

    def __call__(self, slug: str) -> PublicCard:
        card = self._repo.find_by_slug(PublicSlug(slug))
        if card is None:
            raise _not_found()
        return to_public(_ordered(card))
