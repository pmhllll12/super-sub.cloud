"""카드 HTTP 모델. 계약 문서 3장.

`from_attributes` 라 유스케이스가 돌려준 Result DTO 를 그대로 받아 변환한다.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339


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
    # 사람이 정하는 한 줄. 안 정했으면 null (미결 paik 3번).
    tagline: str | None = None


class UpdateMyCardSchema(BaseModel):
    """카드 수정 요청.

    🔴 **필드가 하나뿐인 것이 의도다.** `public_slug` 는 이미 공유된 주소라
    바꾸면 남이 가진 링크가 죽고, `og_image_key` 는 슬러그에서 규칙으로 나온다.
    받을 자리를 아예 안 두는 것이 그 규칙을 지키는 방법이다.

    `null` 이나 공백만 보내면 **지운다** — 안 정한 상태로 돌아간다.
    """

    tagline: str | None = Field(default=None, max_length=20)


class PublicCardResponse(BaseModel):
    """공유 링크로 보는 카드. 내부 카드 id 를 뺀다."""

    model_config = ConfigDict(from_attributes=True)

    public_slug: str
    og_image_key: str
    user: CardOwnerResponse
    titles: list[TitleResponse]
    # 🔴 여기에도 실린다. 안 실으면 **남이 보는 카드만** 밋밋해진다.
    tagline: str | None = None
