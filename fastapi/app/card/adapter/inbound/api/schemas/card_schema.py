"""카드 HTTP 모델. 계약 문서 3장.

`from_attributes` 라 유스케이스가 돌려준 Result DTO 를 그대로 받아 변환한다.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared import Rfc3339


class TitleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    category: str
    granted_at: Rfc3339


class CardOwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nickname: str


class MyCardResponse(BaseModel):
    """내 카드.

    능력치 수치 필드가 없다. `player_card` 에 그런 컬럼이 애초에 없고(부록 D.5),
    `tests/card/test_card_rules.py` 가 이 모델에 금지 필드가 생기지 않는지 지킨다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    public_slug: str
    og_image_key: str
    user: CardOwnerResponse
    titles: list[TitleResponse]


class PublicCardResponse(BaseModel):
    """공유 링크로 보는 카드. 내부 카드 id 를 뺀다."""

    model_config = ConfigDict(from_attributes=True)

    public_slug: str
    og_image_key: str
    user: CardOwnerResponse
    titles: list[TitleResponse]
