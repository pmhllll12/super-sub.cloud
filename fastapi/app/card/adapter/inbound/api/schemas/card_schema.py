"""카드 HTTP 모델. 계약 문서 3장.

`from_attributes` 라 유스케이스가 돌려준 Result DTO 를 그대로 받아 변환한다.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339

_HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class CardStyleSchema(BaseModel):
    """카드 꾸미기 — 바탕 · 로고 · 글자 색 · 글자 자리 · 붓자국(미결 `paik` 3번
    나머지). `PATCH /me/card` 의 `style`, `GET /me/card`·`GET /cards/{slug}`
    양쪽의 `style` 이 다 이 모양이다.

    🔴 **가운데 큰 글자(text)는 여기 없다** — 이미 있는 `tagline` 이 같은
    자리다. `www` 가 04-09 이후 그걸 몰라 `style.text` 를 새로 만들었는데,
    이 마이그레이션에서 `tagline` 쪽으로 합친다.

    🔴 **사진도 여기 없다** — `og_image_key` 처럼 저장 위치가 아직 안
    정해졌다. 사진에 딸린 자리·크기(`photoScale`·`photoX`·`photoY`)와
    통째로 까는 모드(`mode`)도 사진이 없으면 뜻이 없어 같이 뺐다. `www` 는
    그 넷을 그대로 브라우저에만 담아 둔다.

    🔴 **`brush` 상한을 값으로 안 검사한다.** 고를 수 있는 자국 목록
    (`www/src/components/CardMark.tsx` 의 `MARKS`)은 화면 쪽 자산이라 늘어날
    수 있는데, 여기서 정확한 개수로 막으면 자국 하나 늘 때마다 계약을 올려야
    한다. `focus`(미결 `paik` 8번)가 루브릭 항목 실재를 안 보는 것과 같은
    판단 — 형식(정수·구간)만 본다.
    """

    model_config = ConfigDict(extra="forbid")

    bg: str = Field(pattern=_HEX_COLOR)
    logo: str = Field(pattern=_HEX_COLOR)
    text_color: str = Field(pattern=_HEX_COLOR)
    text_x: float = Field(ge=0, le=100)
    text_y: float = Field(ge=0, le=100)
    brush: int = Field(ge=0, le=50)
    brush_color: str = Field(pattern=_HEX_COLOR)
    brush_scale: float = Field(ge=0.1, le=5)
    brush_x: float = Field(ge=-100, le=100)
    brush_y: float = Field(ge=-100, le=100)


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
    # 카드 꾸미기. 안 꾸몄으면 null — 화면이 기본 모습을 그린다.
    style: CardStyleSchema | None = None


class UpdateMyCardSchema(BaseModel):
    """카드 수정 요청.

    🔴 **`public_slug`·`og_image_key` 는 여기 없다.** `public_slug` 는 이미
    공유된 주소라 바꾸면 남이 가진 링크가 죽고, `og_image_key` 는 슬러그에서
    규칙으로 나온다. 받을 자리를 아예 안 두는 것이 그 규칙을 지키는 방법이다.

    **보낸 필드만** 바뀐다(`model_fields_set` 로 가른다, `UpdateVideoSchema`
    와 같은 판단) — 둘 다 안 보내면 아무것도 안 바뀐다. `null` 을 보낸
    필드는 **지운다** — 안 정한 상태로 돌아간다.
    """

    tagline: str | None = Field(default=None, max_length=20)
    style: CardStyleSchema | None = Field(default=None)


class PublicCardResponse(BaseModel):
    """공유 링크로 보는 카드. 내부 카드 id 를 뺀다."""

    model_config = ConfigDict(from_attributes=True)

    public_slug: str
    og_image_key: str
    user: CardOwnerResponse
    titles: list[TitleResponse]
    # 🔴 여기에도 실린다. 안 실으면 **남이 보는 카드만** 밋밋해진다.
    tagline: str | None = None
    style: CardStyleSchema | None = None
