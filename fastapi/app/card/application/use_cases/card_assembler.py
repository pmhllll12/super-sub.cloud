"""엔티티 → DTO 변환.

두 인터랙터가 같은 변환을 쓰므로 한곳에 모았다. **여기까지가 도메인의 마지막
지점이다** — 이 함수들이 돌려준 뒤로는 값 객체가 나가지 않는다.
"""

from __future__ import annotations

from app.card.application.dtos.card_dto import (
    CardOwnerResult,
    MyCardResult,
    PublicCardResult,
    TitleResult,
)
from app.card.domain.entities.card_entity import CardEntity, PublicCardEntity
from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.value_objects.card_owner_vo import CardOwner


def _titles(titles: list[TitleEntity]) -> list[TitleResult]:
    return [
        TitleResult(
            code=t.code,
            label=t.label,
            category=str(t.category),
            granted_at=t.granted_at,
        )
        for t in titles
    ]


def _owner(owner: CardOwner) -> CardOwnerResult:
    return CardOwnerResult(id=owner.id, nickname=owner.nickname)


def to_my_card_result(card: CardEntity) -> MyCardResult:
    return MyCardResult(
        id=card.id,
        public_slug=str(card.public_slug),
        og_image_key=card.og_image_key,
        user=_owner(card.owner),
        titles=_titles(card.titles),
    )


def to_public_card_result(card: PublicCardEntity) -> PublicCardResult:
    return PublicCardResult(
        public_slug=str(card.public_slug),
        og_image_key=card.og_image_key,
        user=_owner(card.owner),
        titles=_titles(card.titles),
    )
