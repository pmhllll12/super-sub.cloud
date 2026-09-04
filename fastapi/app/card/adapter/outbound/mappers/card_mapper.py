"""ORM 행 ↔ 카드 도메인.

순수 함수라 DB 없이 테스트할 수 있다. **정렬하지 않는다** — 표시 순서는
`domain/rules/card_rules.visible_titles` 의 몫이고, 여기서 정렬해 버리면 그 규칙이
실제로 도는지 확인할 수 없게 된다.
"""

from __future__ import annotations

from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.card.adapter.outbound.orm.title_definition_orm import TitleDefinitionOrm
from app.card.adapter.outbound.orm.user_title_orm import UserTitleOrm
from app.card.domain.entities.card_entity import CardEntity
from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.value_objects.card_owner_vo import CardOwner
from app.card.domain.value_objects.public_slug_vo import PublicSlug
from app.card.domain.value_objects.title_category_vo import TitleCategory


def to_title_entity(
    granted: UserTitleOrm, definition: TitleDefinitionOrm
) -> TitleEntity:
    return TitleEntity(
        code=definition.code,
        label=definition.label,
        # 열거형으로 되돌린다. DB 에 CHECK 가 없으므로 여기가 마지막 방어선이다 —
        # 정의되지 않은 분류가 들어 있으면 ValueError 로 크게 실패한다.
        category=TitleCategory(definition.category),
        granted_at=granted.granted_at,
    )


def to_card_entity(
    row: PlayerCardOrm, owner_nickname: str, titles: list[TitleEntity]
) -> CardEntity:
    return CardEntity(
        id=row.id,
        public_slug=PublicSlug(row.public_slug),
        og_image_key=row.og_image_key,
        owner=CardOwner(id=row.user_id, nickname=owner_nickname),
        titles=titles,
        tagline=row.tagline,
    )
