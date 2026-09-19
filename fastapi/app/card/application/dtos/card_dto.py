"""카드 유스케이스가 주고받는 DTO.

값 객체가 아니라 **원시 타입**으로만 담는다. 그래야 라우터가 도메인을 모른다.
`PublicCardResult` 에 `id` 가 없는 것이 계약이다 — 공개 카드는 내부 식별자를
싣지 않는다(SFR-009).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final
from uuid import UUID

# PATCH 에서 "안 보냈다"(그대로 둔다)와 "`null` 을 보냈다"(지운다)를 가르는
# 자리표시자 — `app.analysis.application.dtos.video_dto.UNSET` 과 같은 판단
# 이지만, 컨텍스트끼리 임포트하지 않으므로(`tests/test_architecture.py`)
# 여기 따로 둔다.
UNSET: Final[Any] = object()


@dataclass(frozen=True)
class MyCardQuery:
    user_id: UUID


@dataclass(frozen=True)
class CreateMyCardCommand:
    user_id: UUID


@dataclass(frozen=True)
class CreateMyCardCommand:
    user_id: UUID


@dataclass(frozen=True)
class DeleteMyCardCommand:
    user_id: UUID


@dataclass(frozen=True)
class PublicCardQuery:
    public_slug: str


@dataclass(frozen=True)
class TitleResult:
    code: str
    label: str
    #: 사람이 직접 적은 호칭은 `None` 이다(`paik` 36번) — 분류는 부여되는
    #: 호칭의 것이다. 자세한 이유는 `TitleEntity.category`.
    category: str | None
    granted_at: datetime


@dataclass(frozen=True)
class CardOwnerResult:
    id: UUID
    nickname: str


@dataclass(frozen=True)
class MyCardResult:
    id: UUID
    public_slug: str
    og_image_key: str
    user: CardOwnerResult
    titles: list[TitleResult] = field(default_factory=list)
    tagline: str | None = None
    style: dict | None = None
    #: 카드 사진의 **사전 서명 GET 주소**(2026-09-18). 저장하지 않는다 —
    #: `style["photo_key"]` 에서 읽을 때마다 새로 만든다(유효 시간이 있다).
    #:
    #: 🔴 **`None` 인 경우가 셋이고 전부 정상**이다: 사진을 안 올렸다 ·
    #: 저장소가 설정 안 됐다(로컬) · 키가 있는데 파일이 아직 없다. 화면은
    #: 그때 기본 장식 그림을 그린다.
    photo_url: str | None = None


@dataclass(frozen=True)
class MyCardCreation:
    """생성 요청의 결과.

    `created` 가 응답 코드를 가른다 — 만들었으면 201, 이미 있었으면 200이다.
    카드 자체는 두 경우가 같으므로 `MyCardResult` 를 그대로 싣는다.
    """

    card: MyCardResult
    created: bool


@dataclass(frozen=True)
class MyCardCreation:
    """생성 요청의 결과.

    `created` 가 응답 코드를 가른다 — 만들었으면 201, 이미 있었으면 200이다.
    카드 자체는 두 경우가 같으므로 `MyCardResult` 를 그대로 싣는다.
    """

    card: MyCardResult
    created: bool


@dataclass(frozen=True)
class PublicCardResult:
    public_slug: str
    og_image_key: str
    user: CardOwnerResult
    titles: list[TitleResult] = field(default_factory=list)
    tagline: str | None = None
    style: dict | None = None
    #: 🔴 **여기에도 실린다.** 안 실으면 남이 보는 카드만 사진이 없다
    #: (`tagline`·`style` 을 공개 응답에 실은 것과 같은 이유).
    photo_url: str | None = None


@dataclass(frozen=True)
class CardPhotoUploadCommand:
    user_id: UUID
    #: 브라우저가 **PUT 헤더로 그대로 보낼** 값. 서명에 들어가므로 다르면 403.
    content_type: str


@dataclass(frozen=True)
class CardPhotoUploadResult:
    upload_url: str
    #: 올린 뒤 `PATCH /me/card` 의 `style.photo_key` 로 되돌려 보낼 값.
    storage_key: str
    expires_in: int
