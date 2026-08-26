"""선수 카드. 계약 문서 3장."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app import stubs
from app.deps import require_token
from app.errors import ApiError
from app.schemas import CardResponse, PublicCardResponse

router = APIRouter(tags=["cards"])


@router.get("/me/card", response_model=CardResponse)
def read_my_card(_: Annotated[str, Depends(require_token)]) -> CardResponse:
    return stubs.my_card()


@router.get("/cards/{public_slug}", response_model=PublicCardResponse)
def read_public_card(public_slug: str) -> PublicCardResponse:
    """공유용이라 인증하지 않는다 (SFR-009).

    없는 슬러그를 눌러볼 수 있도록 데모 슬러그만 성공한다.
    """
    if public_slug != stubs.DEMO_SLUG:
        raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")
    return stubs.public_card()
