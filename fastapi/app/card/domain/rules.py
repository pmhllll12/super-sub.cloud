"""카드 컨텍스트의 규칙.

**부록 D.5 의 설계 원칙이 사는 곳이다.** 스키마로 막아 놨어도 응답에서 되살아나면
무의미하므로 여기서 한 번 더 막고 테스트로 고정한다.
"""

from __future__ import annotations

from app.card.domain.entities import Card, PublicCard, Title

# 카드에 실려서는 안 되는 이름들. 3.5 — "카드에 수치 능력치를 노출하지 않는다".
# player_card 에 그런 컬럼이 애초에 없으므로 조회 경로로도 새면 안 된다.
FORBIDDEN_CARD_FIELDS = frozenset(
    {
        "score", "rating", "stat", "stats", "level", "rank", "ranking",
        "grade", "point", "points", "ability", "abilities", "overall", "tier",
    }
)


def to_public(card: Card) -> PublicCard:
    """공개용으로 깎는다.

    내부 카드 id 를 떨어뜨리는 것이 요점이다. 공유 링크는 슬러그로만 접근하며
    (SFR-009) 카드 id 를 알아야 할 이유가 없다.
    """
    return PublicCard(
        public_slug=card.public_slug,
        og_image_key=card.og_image_key,
        owner=card.owner,
        titles=list(card.titles),
    )


def visible_titles(granted: list[Title]) -> list[Title]:
    """카드에 표시할 호칭.

    **부여된 것만 들어온다.** "못 받았다"를 값으로 만들지 않는다 — 미달을 `False` 로
    표시하면 그 순간 부정 표식이 된다(3.5).

    최근에 받은 것을 앞에 둔다. 카드가 좁아서 다 못 보여줄 수 있다.
    """
    return sorted(granted, key=lambda t: t.granted_at, reverse=True)
