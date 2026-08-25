"""카드·호칭 HTTP 경계. 계약 문서 3장."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.cards.domain import Card, PublicCard
from app.cards.schemas import (
    CardOwnerResponse,
    CardResponse,
    PublicCardResponse,
    TitleResponse,
)
from app.cards.service import CardService
from app.deps import CurrentUserId, get_card_service

router = APIRouter(tags=["cards"])

_Service = Annotated[CardService, Depends(get_card_service)]


def _titles(card: Card | PublicCard) -> list[TitleResponse]:
    return [
        TitleResponse(
            code=t.code, label=t.label, category=t.category, granted_at=t.granted_at
        )
        for t in card.titles
    ]


def _owner(card: Card | PublicCard) -> CardOwnerResponse:
    return CardOwnerResponse(id=card.owner.id, nickname=card.owner.nickname)


@router.get("/me/card", response_model=CardResponse)
def read_my_card(user_id: CurrentUserId, service: _Service) -> CardResponse:
    card = service.my_card(user_id)
    return CardResponse(
        id=card.id,
        public_slug=card.public_slug,
        og_image_key=card.og_image_key,
        user=_owner(card),
        titles=_titles(card),
    )


@router.get("/cards/{public_slug}", response_model=PublicCardResponse)
def read_public_card(public_slug: str, service: _Service) -> PublicCardResponse:
    """공유용이라 인증하지 않는다 (SFR-009)."""
    card = service.public_card(public_slug)
    return PublicCardResponse(
        public_slug=card.public_slug,
        og_image_key=card.og_image_key,
        user=_owner(card),
        titles=_titles(card),
    )
