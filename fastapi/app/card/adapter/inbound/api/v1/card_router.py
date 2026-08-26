"""카드 라우터. 계약 문서 3장.

**여기는 도메인을 모른다.** Query DTO 로 바꿔 유스케이스에 넘기고, 돌아온 Result DTO 를
`response_model` 이 응답 스키마로 변환한다.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.card.adapter.inbound.api.schemas.card_schema import (
    MyCardResponse,
    PublicCardResponse,
)
from app.card.application.dtos.card_dto import (
    MyCardQuery,
    MyCardResult,
    PublicCardQuery,
    PublicCardResult,
)
from app.card.dependencies.my_card_provider import MyCardUseCaseDep
from app.card.dependencies.public_card_provider import PublicCardUseCaseDep
from app.core.deps import CurrentUserId

card_router = APIRouter(tags=["cards"])


@card_router.get("/me/card", response_model=MyCardResponse)
def read_my_card(user_id: CurrentUserId, use_case: MyCardUseCaseDep) -> MyCardResult:
    return use_case(MyCardQuery(user_id=user_id))


@card_router.get("/cards/{public_slug}", response_model=PublicCardResponse)
def read_public_card(
    public_slug: str, use_case: PublicCardUseCaseDep
) -> PublicCardResult:
    """공유용이라 인증하지 않는다 (SFR-009)."""
    return use_case(PublicCardQuery(public_slug=public_slug))
