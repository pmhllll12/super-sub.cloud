"""card/domain/rules.py

**부록 D.5 의 설계 원칙을 지키는 테스트가 여기 있다.** 예전에는 셸 스크립트가 응답
JSON 을 grep 해서 확인했는데, 그건 "지금 응답에 그 글자가 없다"만 말해줬다.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.card.adapter.inbound.schemas import (
    CardResponse,
    PublicCardResponse,
    TitleResponse,
)
from app.card.domain.entities import Card, CardOwner, Title
from app.card.domain.rules import FORBIDDEN_CARD_FIELDS, to_public, visible_titles
from app.card.domain.value_objects import PublicSlug, TitleCategory


def _title(code: str, y: int, mo: int, d: int) -> Title:
    return Title(
        code=code,
        label=code,
        category=TitleCategory.STRENGTH,
        granted_at=datetime(y, mo, d, tzinfo=timezone.utc),
    )


def _card() -> Card:
    return Card(
        id=uuid4(),
        public_slug=PublicSlug("hong-gildong-4f2a"),
        og_image_key="cards/x.png",
        owner=CardOwner(id=uuid4(), nickname="홍길동"),
        titles=[_title("old", 2026, 8, 1), _title("new", 2026, 8, 20)],
    )


class TestToPublic:
    def test_내부_카드_id_를_떨어뜨린다(self):
        # 공유 링크는 슬러그로만 접근한다(SFR-009). 카드 id 를 알 이유가 없다.
        assert not hasattr(to_public(_card()), "id")

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
        assert len(visible_titles([_title("a", 2026, 8, 1), _title("b", 2026, 8, 2)])) == 2


class TestDesignPrinciples:
    """부록 D.5 — 스키마로 막은 것을 도메인·응답 모델에서도 막는다."""

    def test_카드_엔티티에_수치_능력치가_없다(self):
        # 3.5 — 카드에 수치 능력치를 노출하지 않는다. player_card 에 그런 컬럼이
        # 애초에 없으므로 조회 경로로도 새면 안 된다.
        for cls in (Card, PublicCardResponse, CardResponse):
            names = (
                cls.model_fields
                if hasattr(cls, "model_fields")
                else cls.__dataclass_fields__
            )
            offending = {n for n in names if n.lower() in FORBIDDEN_CARD_FIELDS}
            assert not offending, f"{cls.__name__} 에 수치 필드가 생겼다: {offending}"

    def test_호칭에_미부여_표식_필드가_없다(self):
        # 3.5 — earned=false 를 두는 순간 그것이 부정 표식이 된다.
        for name in ("earned", "achieved", "unlocked"):
            assert name not in TitleResponse.model_fields
            assert name not in Title.__dataclass_fields__

    def test_공개_카드_모델에만_id_가_없다(self):
        assert "id" not in PublicCardResponse.model_fields
        assert "id" in CardResponse.model_fields


class TestTitleCategory:
    def test_부록_D_가_정의한_셋만_있다(self):
        assert {c.value for c in TitleCategory} == {"강점", "활동", "용병"}
