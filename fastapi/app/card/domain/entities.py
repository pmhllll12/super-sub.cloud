"""카드 컨텍스트의 엔티티. 부록 D 도메인 ③ 의 테이블에 대응한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.card.domain.value_objects import PublicSlug, TitleCategory


@dataclass(frozen=True)
class Title:
    """`user_title` 한 행 + `title_definition` 의 표시 정보.

    **부여된 것만 존재한다.** 미달을 `False` 로 담지 않는다 — 부록 D 도메인 ③ 이
    미부여 방식으로 설계된 이유다(3.5).
    """

    code: str
    label: str
    category: TitleCategory
    granted_at: datetime


@dataclass(frozen=True)
class CardOwner:
    id: UUID
    nickname: str


@dataclass(frozen=True)
class Card:
    """`player_card` 한 행.

    **능력치 컬럼이 없다.** 수치는 `analysis_metric_value` 에만 있고 리포트 경로로만
    나간다(부록 D.5). 이 엔티티에 점수 필드를 추가하는 순간 3.5 가 깨진다.
    """

    id: UUID
    public_slug: PublicSlug
    og_image_key: str
    owner: CardOwner
    titles: list[Title]


@dataclass(frozen=True)
class PublicCard:
    """공유 링크로 나가는 카드. 내부 id 가 없다."""

    public_slug: PublicSlug
    og_image_key: str
    owner: CardOwner
    titles: list[Title]
