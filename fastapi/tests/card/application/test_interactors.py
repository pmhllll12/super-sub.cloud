"""card/application/use_cases/ — 가짜 저장소를 끼워서 돌린다."""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.card.application.dtos.card_dto import (
    CreateMyCardCommand,
    MyCardQuery,
    PublicCardQuery,
)
from app.card.application.ports.output.card_port import CardPort
from app.card.application.use_cases.create_my_card_interactor import (
    CreateMyCardInteractor,
)
from app.card.application.use_cases.my_card_interactor import MyCardInteractor
from app.card.application.use_cases.public_card_interactor import (
    PublicCardInteractor,
)
from app.card.domain.entities.card_entity import CardEntity
from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.value_objects.card_owner_vo import CardOwner
from app.card.domain.value_objects.public_slug_vo import PublicSlug
from app.card.domain.value_objects.title_category_vo import TitleCategory
from app.core.errors import ApiError

_OWNER_ID = uuid4()
_SLUG = "hong-gildong-4f2a"


def _card() -> CardEntity:
    return CardEntity(
        id=uuid4(),
        public_slug=PublicSlug(_SLUG),
        og_image_key="cards/x.png",
        owner=CardOwner(id=_OWNER_ID, nickname="홍길동"),
        titles=[
            TitleEntity(
                code="old",
                label="옛것",
                category=TitleCategory.ACTIVITY,
                granted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            ),
            TitleEntity(
                code="new",
                label="새것",
                category=TitleCategory.STRENGTH,
                granted_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
            ),
        ],
    )


class FakeCardRepository(CardPort):
    def __init__(self) -> None:
        # 저장소가 실제로 불렸는지 보려고 남긴다. "이미 있으면 만들지 않는다"는
        # 결과만으로 확인되지 않는다 — 카드는 어느 쪽이든 돌아오기 때문이다.
        self.created_for: list[UUID] = []

    def find_by_owner(self, user_id: UUID) -> CardEntity | None:
        return _card() if user_id == _OWNER_ID else None

    def find_by_slug(self, slug: PublicSlug) -> CardEntity | None:
        return _card() if slug == PublicSlug(_SLUG) else None

    def create_for_owner(self, user_id: UUID) -> CardEntity:
        self.created_for.append(user_id)
        return replace(
            _card(),
            owner=CardOwner(id=user_id, nickname="새 사람"),
            titles=[],
        )


class TestMyCardInteractor:
    def test_호칭이_최신순으로_정렬돼_나온다(self):
        result = MyCardInteractor(FakeCardRepository())(MyCardQuery(user_id=_OWNER_ID))
        assert [t.code for t in result.titles] == ["new", "old"]

    def test_결과는_원시_타입만_담는다(self):
        # 값 객체가 새어 나가면 라우터가 도메인을 알게 된다.
        result = MyCardInteractor(FakeCardRepository())(MyCardQuery(user_id=_OWNER_ID))
        assert isinstance(result.public_slug, str)
        assert isinstance(result.titles[0].category, str)

    def test_카드가_없으면_404(self):
        with pytest.raises(ApiError) as exc:
            MyCardInteractor(FakeCardRepository())(MyCardQuery(user_id=uuid4()))
        assert exc.value.status_code == 404
        assert exc.value.code == "CARD_NOT_FOUND"


class TestPublicCardInteractor:
    def test_내부_id_없이_돌려준다(self):
        result = PublicCardInteractor(FakeCardRepository())(
            PublicCardQuery(public_slug=_SLUG)
        )
        assert not hasattr(result, "id")

    def test_없는_슬러그면_404(self):
        with pytest.raises(ApiError) as exc:
            PublicCardInteractor(FakeCardRepository())(
                PublicCardQuery(public_slug="no-such-slug")
            )
        assert exc.value.code == "CARD_NOT_FOUND"


class TestCreateMyCardInteractor:
    def test_없으면_만든다(self):
        repo = FakeCardRepository()
        new_id = uuid4()
        result = CreateMyCardInteractor(repo)(CreateMyCardCommand(user_id=new_id))
        assert result.created is True
        assert repo.created_for == [new_id]

    def test_이미_있으면_저장소를_건드리지_않는다(self):
        repo = FakeCardRepository()
        result = CreateMyCardInteractor(repo)(CreateMyCardCommand(user_id=_OWNER_ID))
        assert result.created is False
        assert repo.created_for == []

    def test_이미_있으면_그_카드를_돌려준다(self):
        result = CreateMyCardInteractor(FakeCardRepository())(
            CreateMyCardCommand(user_id=_OWNER_ID)
        )
        assert result.card.public_slug == _SLUG

    def test_호칭_정렬이_조회와_같다(self):
        """생성 응답만 정렬이 다르면 클라이언트가 파서를 둘 들어야 한다."""
        result = CreateMyCardInteractor(FakeCardRepository())(
            CreateMyCardCommand(user_id=_OWNER_ID)
        )
        assert [t.code for t in result.card.titles] == ["new", "old"]

    def test_결과는_원시_타입만_담는다(self):
        result = CreateMyCardInteractor(FakeCardRepository())(
            CreateMyCardCommand(user_id=uuid4())
        )
        assert isinstance(result.card.public_slug, str)
