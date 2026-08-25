"""card/application/use_cases.py — 가짜 저장소를 끼워서 돌린다."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.card.application.use_cases import MyCardUseCase, PublicCardUseCase
from app.card.domain.entities import Card, CardOwner, Title
from app.card.domain.value_objects import PublicSlug, TitleCategory
from app.errors import ApiError

_OWNER_ID = uuid4()
_SLUG = PublicSlug("hong-gildong-4f2a")


def _card() -> Card:
    return Card(
        id=uuid4(),
        public_slug=_SLUG,
        og_image_key="cards/x.png",
        owner=CardOwner(id=_OWNER_ID, nickname="홍길동"),
        titles=[
            Title(
                code="old",
                label="옛것",
                category=TitleCategory.ACTIVITY,
                granted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            ),
            Title(
                code="new",
                label="새것",
                category=TitleCategory.STRENGTH,
                granted_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
            ),
        ],
    )


class FakeCardRepository:
    def find_by_owner(self, user_id: UUID) -> Card | None:
        return _card() if user_id == _OWNER_ID else None

    def find_by_slug(self, slug: PublicSlug) -> Card | None:
        return _card() if slug == _SLUG else None


class TestMyCard:
    def test_호칭이_최신순으로_정렬돼_나온다(self):
        card = MyCardUseCase(FakeCardRepository())(_OWNER_ID)
        assert [t.code for t in card.titles] == ["new", "old"]

    def test_카드가_없으면_404(self):
        with pytest.raises(ApiError) as exc:
            MyCardUseCase(FakeCardRepository())(uuid4())
        assert exc.value.status_code == 404
        assert exc.value.code == "CARD_NOT_FOUND"


class TestPublicCard:
    def test_내부_id_없이_돌려준다(self):
        card = PublicCardUseCase(FakeCardRepository())(str(_SLUG))
        assert not hasattr(card, "id")

    def test_없는_슬러그면_404(self):
        with pytest.raises(ApiError) as exc:
            PublicCardUseCase(FakeCardRepository())("no-such-slug")
        assert exc.value.code == "CARD_NOT_FOUND"
