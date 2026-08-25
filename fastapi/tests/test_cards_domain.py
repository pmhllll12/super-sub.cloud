"""카드·호칭 도메인 규칙.

**부록 D.5의 설계 원칙을 지키는 테스트가 여기 있다.** 예전에는 셸 스크립트가 응답
JSON을 grep 해서 확인했는데, 그건 "지금 응답에 그 글자가 없다"만 말해줄 뿐이었다.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.cards.domain import (
    FORBIDDEN_CARD_FIELDS,
    Card,
    CardOwner,
    Title,
    to_public,
    visible_titles,
)
from app.cards.schemas import CardResponse, PublicCardResponse


def _title(code: str, y: int, mo: int, d: int) -> Title:
    return Title(
        code=code,
        label=code,
        category="강점",
        granted_at=datetime(y, mo, d, tzinfo=timezone.utc),
    )


def _card() -> Card:
    return Card(
        id=uuid4(),
        public_slug="hong-gildong-4f2a",
        og_image_key="cards/x.png",
        owner=CardOwner(id=uuid4(), nickname="홍길동"),
        titles=[_title("old", 2026, 8, 1), _title("new", 2026, 8, 20)],
    )


class TestToPublic:
    def test_내부_카드_id_를_떨어뜨린다(self):
        # 공유 링크는 슬러그로만 접근한다(SFR-009). 카드 id 를 알아야 할 이유가 없다.
        public = to_public(_card())
        assert not hasattr(public, "id")

    def test_나머지는_그대로_넘긴다(self):
        card = _card()
        public = to_public(card)
        assert public.public_slug == card.public_slug
        assert public.og_image_key == card.og_image_key
        assert public.owner == card.owner


class TestVisibleTitles:
    def test_최근에_받은_것이_앞에_온다(self):
        result = visible_titles([_title("old", 2026, 8, 1), _title("new", 2026, 8, 20)])
        assert [t.code for t in result] == ["new", "old"]

    def test_호칭이_없으면_빈_목록이고_그것이_정상이다(self):
        # "아직 못 받았다"를 값으로 만들지 않는다. 빈 배열이 곧 미부여 상태다.
        assert visible_titles([]) == []

    def test_개수를_늘리거나_줄이지_않는다(self):
        titles = [_title("a", 2026, 8, 1), _title("b", 2026, 8, 2)]
        assert len(visible_titles(titles)) == 2


class TestDesignPrinciples:
    """부록 D.5 — 스키마로 막은 것을 응답 모델에서도 막는다."""

    def test_카드_응답에_수치_능력치_필드가_없다(self):
        # 3.5 — 카드에 수치 능력치를 노출하지 않는다. player_card 에 그런 컬럼이
        # 애초에 없으므로 조회 경로로도 새면 안 된다.
        for model in (CardResponse, PublicCardResponse):
            offending = {
                name
                for name in model.model_fields
                if name.lower() in FORBIDDEN_CARD_FIELDS
            }
            assert not offending, f"{model.__name__} 에 수치 필드가 생겼다: {offending}"

    def test_호칭에_미부여_표식_필드가_없다(self):
        # 3.5 — 호칭은 미부여 방식으로만 작동한다. earned=false 를 두는 순간
        # 그것이 부정 표식이 된다.
        from app.cards.schemas import TitleResponse

        assert "earned" not in TitleResponse.model_fields
        assert "achieved" not in TitleResponse.model_fields

    def test_공개_카드_모델에_id_가_없다(self):
        assert "id" not in PublicCardResponse.model_fields
        assert "id" in CardResponse.model_fields
