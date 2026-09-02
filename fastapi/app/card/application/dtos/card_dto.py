"""카드 유스케이스가 주고받는 DTO.

값 객체가 아니라 **원시 타입**으로만 담는다. 그래야 라우터가 도메인을 모른다.
`PublicCardResult` 에 `id` 가 없는 것이 계약이다 — 공개 카드는 내부 식별자를
싣지 않는다(SFR-009).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


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
class PublicCardQuery:
    public_slug: str


@dataclass(frozen=True)
class TitleResult:
    code: str
    label: str
    category: str
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
