"""카드·호칭 규칙.

**부록 D.5 의 설계 원칙이 사는 곳이다.** 스키마로 막아 놨어도 응답에서 되살아나면
무의미하므로 여기서 한 번 더 막고 테스트로 고정한다.
"""

from __future__ import annotations

from uuid import UUID

from uuid import UUID

from app.card.domain.entities.card_entity import CardEntity, PublicCardEntity
from app.card.domain.entities.title_entity import TitleEntity

# 카드에 실려서는 안 되는 이름들. 3.5 — "카드에 수치 능력치를 노출하지 않는다".
# player_card 에 그런 컬럼이 애초에 없으므로 조회 경로로도 새면 안 된다.
FORBIDDEN_CARD_FIELDS = frozenset(
    {
        "score", "rating", "stat", "stats", "level", "rank", "ranking",
        "grade", "point", "points", "ability", "abilities", "overall", "tier",
    }
)


def og_image_key_for(card_id: UUID) -> str:
    """공유 미리보기 이미지의 저장 키.

    ⚠️ **아직 그 위치에 파일이 없다.** 이미지 생성도, 파일을 어디에 둘지도 정해지지
    않았다(SFR-001 의 저장 위치 결정과 같은 갈래다). 지금은 **키를 정하는 규칙만**
    두고 값을 채운다 — 컬럼이 NOT NULL 이라 비워 둘 수 없고, 나중에 생성기가
    붙을 때 이 규칙이 그대로 경로가 된다.

    지금 이 값을 그리는 클라이언트는 없다(`www` 의 카드 화면은 고정 장식 이미지를
    쓴다). 그리기 시작하면 **생성기가 먼저 있어야 한다.**
    """
    return f"cards/{card_id}.png"


def og_image_key_for(card_id: UUID) -> str:
    """공유 미리보기 이미지의 저장 키.

    ⚠️ **아직 그 위치에 파일이 없다.** 이미지 생성도, 파일을 어디에 둘지도 정해지지
    않았다(SFR-001 의 저장 위치 결정과 같은 갈래다). 지금은 **키를 정하는 규칙만**
    두고 값을 채운다 — 컬럼이 NOT NULL 이라 비워 둘 수 없고, 나중에 생성기가 붙을
    때 이 규칙이 그대로 경로가 된다.

    지금 이 값을 그리는 클라이언트는 없다(`www` 의 카드 화면은 고정 장식 이미지를
    쓴다). 그리기 시작하면 **생성기가 먼저 있어야 한다.**
    """
    return f"cards/{card_id}.png"


def to_public(card: CardEntity) -> PublicCardEntity:
    """공개용으로 깎는다.

    내부 카드 id 를 떨어뜨리는 것이 요점이다. 공유 링크는 슬러그로만 접근하며
    (SFR-009) 카드 id 를 알아야 할 이유가 없다.
    """
    return PublicCardEntity(
        public_slug=card.public_slug,
        og_image_key=card.og_image_key,
        owner=card.owner,
        titles=list(card.titles),
    )


def visible_titles(granted: list[TitleEntity]) -> list[TitleEntity]:
    """카드에 표시할 호칭.

    **부여된 것만 들어온다.** "못 받았다"를 값으로 만들지 않는다(3.5).

    최근에 받은 것을 앞에 둔다. 카드가 좁아서 다 못 보여줄 수 있다.
    """
    return sorted(granted, key=lambda t: t.granted_at, reverse=True)
