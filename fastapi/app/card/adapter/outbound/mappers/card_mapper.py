"""ORM 행 ↔ 카드 도메인.

순수 함수라 DB 없이 테스트할 수 있다. **정렬하지 않는다** — 표시 순서는
`domain/rules/card_rules.visible_titles` 의 몫이고, 여기서 정렬해 버리면 그 규칙이
실제로 도는지 확인할 수 없게 된다.
"""

from __future__ import annotations

from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.card.adapter.outbound.orm.title_definition_orm import TitleDefinitionOrm
from app.card.adapter.outbound.orm.user_custom_title_orm import UserCustomTitleOrm
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


def to_custom_title_entity(row: UserCustomTitleOrm) -> TitleEntity:
    """사람이 직접 적은 호칭을 **부여된 호칭과 같은 모양**으로 만든다
    (`paik` 36번).

    화면이 `titles[]` 하나만 그리므로 여기서 모양을 맞춘다.

    | 칸 | 무엇을 넣나 |
    |---|---|
    | `code` | `custom:<행 id>` — 정의 코드가 아니라는 것이 이름에 보이고, 사람마다·칩마다 **유일**하다(화면이 키로 써도 안 겹친다) |
    | `category` | **`None`** — 분류는 부여되는 호칭의 것이고, 사람이 적은 글에 분류를 매길 사람이 없다(그 항목의 「하지 말 것」). 새 분류를 만들지 않은 이유는 `TitleCategory` 주석 참고 |
    | `granted_at` | 적은 시각. 「받은 시각」과 뜻이 다르지만 **정렬 축이 하나여야** 부여된 것과 섞어 최근순으로 줄 수 있다 |
    """
    return TitleEntity(
        code=f"custom:{row.id}",
        label=row.label,
        category=None,
        granted_at=row.created_at,
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
        style=row.style,
    )
