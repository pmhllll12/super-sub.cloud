"""카드 라우터. 계약 문서 3장.

**여기는 도메인을 모른다.** Query DTO 로 바꿔 유스케이스에 넘기고, 돌아온 Result DTO 를
`response_model` 이 응답 스키마로 변환한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.card.adapter.inbound.api.schemas.card_schema import (
    MyCardResponse,
    PublicCardResponse,
    UpdateMyCardSchema,
)
from app.card.application.dtos.card_dto import (
    CreateMyCardCommand,
    MyCardQuery,
    MyCardResult,
    PublicCardQuery,
    PublicCardResult,
)
from app.card.application.ports.input.update_my_card_use_case import (
    UpdateMyCardCommand,
)
from app.card.dependencies.create_my_card_provider import CreateMyCardUseCaseDep
from app.card.dependencies.my_card_provider import MyCardUseCaseDep
from app.card.dependencies.public_card_provider import PublicCardUseCaseDep
from app.card.dependencies.update_my_card_provider import UpdateMyCardUseCaseDep
from app.core.deps import CurrentUserId

card_router = APIRouter(tags=["cards"])


@card_router.get("/me/card", response_model=MyCardResponse)
def read_my_card(user_id: CurrentUserId, use_case: MyCardUseCaseDep) -> MyCardResult:
    return use_case(MyCardQuery(user_id=user_id))


@card_router.post(
    "/me/card",
    response_model=MyCardResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "이미 카드가 있었다. 있는 것을 그대로 돌려준다"}},
)
def create_my_card(
    user_id: CurrentUserId,
    use_case: CreateMyCardUseCaseDep,
    response: Response,
) -> MyCardResult:
    """카드를 만든다 (계약 문서 3장).

    **멱등이다.** 두 번 불러도 카드는 하나고 슬러그도 그대로다 — 두 번째부터는
    200 이 온다. 클라이언트가 재시도해도 공유 링크가 바뀌면 안 되기 때문이다.
    """
    creation = use_case(CreateMyCardCommand(user_id=user_id))
    if not creation.created:
        response.status_code = status.HTTP_200_OK
    return creation.card


@card_router.patch("/me/card", response_model=MyCardResponse)
def update_my_card(
    body: UpdateMyCardSchema,
    user_id: CurrentUserId,
    use_case: UpdateMyCardUseCaseDep,
) -> MyCardResult:
    """카드에서 **사람이 정하는 한 줄**을 바꾼다 (미결 `paik` 3번).

    지금까지 카드는 만들고 나면 손댈 것이 없었다 — 별명이 화면의 붙박이 상수라
    **모든 카드가 글자까지 똑같았다.**

    | | |
    |---|---|
    | `{"tagline": "THREE LUNGS"}` | 정한다 (20자까지) |
    | `{"tagline": null}` 또는 `{"tagline": "  "}` | **지운다** — 안 정한 상태로 |
    | 404 `CARD_NOT_FOUND` | 카드가 없다. **여기서 만들지 않는다** — 만드는 자리는 `POST /me/card` 하나다 |

    🔴 **`public_slug` 는 못 바꾼다.** 이미 공유된 주소라 바꾸면 남이 가진 링크가
    죽는다. 요청 본문에 그 자리를 아예 두지 않았다.
    """
    return use_case(
        UpdateMyCardCommand(user_id=user_id, tagline=body.tagline)
    )


@card_router.get("/cards/{public_slug}", response_model=PublicCardResponse)
def read_public_card(
    public_slug: str, use_case: PublicCardUseCaseDep
) -> PublicCardResult:
    """공유용이라 인증하지 않는다 (SFR-009)."""
    return use_case(PublicCardQuery(public_slug=public_slug))
