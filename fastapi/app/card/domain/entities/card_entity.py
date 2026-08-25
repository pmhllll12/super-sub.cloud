"""`player_card` 에 대응하는 엔티티. 부록 D 도메인 ③."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.value_objects.card_owner_vo import CardOwner
from app.card.domain.value_objects.public_slug_vo import PublicSlug


@dataclass(frozen=True)
class CardEntity:
    """한 사람의 카드 1장.

    **능력치 컬럼이 없다.** 수치는 `analysis_metric_value` 에만 있고 리포트 경로로만
    나간다(부록 D.5). **이 엔티티에 점수 필드를 추가하는 순간 3.5 가 깨진다** —
    `tests/card/test_card_rules.py` 가 그것을 막는다.
    """

    id: UUID
    public_slug: PublicSlug
    og_image_key: str
    owner: CardOwner
    titles: list[TitleEntity]


@dataclass(frozen=True)
class PublicCardEntity:
    """공유 링크로 나가는 카드. 내부 id 가 없다."""

    public_slug: PublicSlug
    og_image_key: str
    owner: CardOwner
    titles: list[TitleEntity]
