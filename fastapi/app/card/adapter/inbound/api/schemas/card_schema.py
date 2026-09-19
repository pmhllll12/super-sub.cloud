"""카드 HTTP 모델. 계약 문서 3장.

`from_attributes` 라 유스케이스가 돌려준 Result DTO 를 그대로 받아 변환한다.
"""

from __future__ import annotations

from uuid import UUID

from typing import Literal

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

    🔴 **정정 (2026-09-18, 사용자 요청): 사진이 들어왔다.** 앞서 여기에
    「사진도 여기 없다 — 저장 위치가 아직 안 정해졌다」고 적어 두었는데,
    자리를 정했다: **바이트는 S3, 여기에는 키만** 둔다
    (`cards/photos/<user_id>/…`, `card_rules.build_photo_key`). `style` 이
    JSON 컬럼이라 **마이그레이션은 없다.**

    🔴 **다섯 칸은 전부 기본값이 있다.** 위 아홉은 필수인데, 새 칸을 필수로
    두면 **지금 돌고 있는 클라이언트가 전부 422** 가 된다 — 사진을 안 쓰는
    쪽은 보내지 않는다.

    🔴 **여기에 그림을 담지 않는다.** data URL 로 담으면 카드를 읽는 모든
    응답에 사진이 실리는데, 스쿼드 판 하나가 자리마다 카드를 부르므로 5~7장이
    매번 함께 나간다. 읽을 주소는 응답의 `photo_url`(사전 서명)이다.

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

    # --- 사진 (2026-09-18) ---------------------------------------------------
    # 🔴 **그림이 아니라 S3 키다.** `null` 이면 사진을 안 쓴다는 뜻이고, 그때
    #    나머지 넷은 뜻이 없다(화면이 기본 장식 그림을 그린다).
    # 🔴 **남의 키를 못 쓴다** — 저장할 때 `owns_photo_key` 로 접두사를
    #    대조한다. 여기서 길이만 보는 것은 형식과 권한이 다른 층이라서다.
    photo_key: str | None = Field(default=None, max_length=200)
    # 카드 안에서 사진을 얼마나 키워 놓았는가. 1 이 원래 크기다.
    photo_scale: float = Field(default=1, ge=0.1, le=5)
    # 사진의 자리(%). 글자 자리(`text_x`)와 달리 **음수가 된다** — 사진은
    # 칸보다 크게 잡아 놓고 밀어 넣는 것이라 왼쪽·위로 넘어간다.
    photo_x: float = Field(default=0, ge=-100, le=100)
    photo_y: float = Field(default=0, ge=-100, le=100)
    # 누끼 인물(`cutout`)이냐 카드를 통째로 덮느냐(`full`).
    mode: Literal["cutout", "full"] = "cutout"


class TitleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    # 🔴 **사람이 직접 적은 호칭은 `null` 이다**(`paik` 36번, 2026-09-16).
    # 그 경우 `code` 가 `custom:` 으로 시작한다.
    category: str | None
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
    # 🔴 **사진을 읽을 주소**(2026-09-18). 사전 서명이라 **유효 시간이 있고
    #    저장되지 않는다** — 부를 때마다 새로 만든다. `style.photo_key` 에서
    #    나오며, 사진이 없거나 저장소가 설정 안 됐으면 `null` 이다.
    photo_url: str | None = None


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
    # 사람이 직접 적는 호칭 **전체 목록**(`paik` 36번). 보낸 목록이 그대로
    # 남는다 — 부분 병합이 아니다. `null` 이나 `[]` 면 전부 지운다.
    # 🔴 `tagline` 을 재활용하지 않은 이유는 그 칸이 카드 가운데 큰 글자로
    # 이미 쓰이고 있어서다(그 항목의 「하지 말 것」).
    titles: list[str] | None = Field(default=None, max_length=3)


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
    # 🔴 여기에도 실린다 — 안 실으면 **남이 보는 카드만** 사진이 없다.
    photo_url: str | None = None


class CardPhotoUploadSchema(BaseModel):
    """카드 사진 올릴 자리 요청 (2026-09-18).

    🔴 **확장자를 받지 않는다** — 타입 하나만 받고 확장자는 서버가 정한다
    (`extension_for_content_type`). 둘 다 받으면 `image/jpeg` 라면서 `.html`
    로 올리는 키가 생긴다.
    """

    model_config = ConfigDict(extra="forbid")

    # 🔴 브라우저가 **PUT 헤더로 그대로 보내야** 하는 값이다 — 서명에 들어가서
    #    다르면 S3 가 403 을 준다.
    content_type: str = Field(max_length=100)


class CardPhotoUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upload_url: str
    #: 올린 뒤 `PATCH /me/card` 의 `style.photo_key` 로 되돌려 보낸다.
    storage_key: str
    expires_in: int
