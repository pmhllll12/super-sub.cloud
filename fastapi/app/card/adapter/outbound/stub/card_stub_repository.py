"""고정 데이터 저장소. DB 가 붙으면 옆에 `card_pg_repository.py` 를 만든다.

지금은 ORM 이 없어서 `mappers/` 도 없다. PostgreSQL 구현이 들어올 때
`adapter/outbound/orm/player_card_orm.py` 와 `adapter/outbound/mappers/card_mapper.py`
가 함께 생긴다.

> ⚠️ **이 파일만 `user` 컨텍스트를 임포트한다.** 데모 카드의 주인을 데모 사용자와
> 맞추기 위해서다. **스텁끼리의 임포트라 둘 다 DB 가 붙는 순간 함께 사라진다.**
> 포트·인터랙터·라우터에는 이 의존이 없다 — `find_by_owner` 가 `user_id` 를
> 인자로 받기 때문이다.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.card.application.ports.output.card_port import CardPort
from app.card.domain.entities.card_entity import CardEntity
from app.card.domain.entities.title_entity import TitleEntity
from app.card.domain.rules.card_rules import og_image_key_for
from app.card.domain.value_objects.card_owner_vo import CardOwner
from app.card.domain.value_objects.public_slug_vo import PublicSlug
from app.card.domain.value_objects.title_category_vo import TitleCategory
from app.user.adapter.outbound.stub.user_stub_repository import DEMO_USER_ID

DEMO_SLUG = "hong-gildong-4f2a"

_CARD_ID = UUID("7b4d1a08-5c39-4e62-8f77-91ac3e0d4b25")


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


_CARD = CardEntity(
    id=_CARD_ID,
    public_slug=PublicSlug(DEMO_SLUG),
    og_image_key=f"cards/{_CARD_ID}.png",
    owner=CardOwner(id=DEMO_USER_ID, nickname="홍길동"),
    titles=[
        # 일부러 오래된 것을 먼저 둔다. visible_titles 가 최신 순으로 정렬하는지
        # 확인하려면 입력이 정렬돼 있으면 안 된다.
        TitleEntity(
            code="weekend_regular",
            label="주말 개근",
            category=TitleCategory.ACTIVITY,
            granted_at=_at(2026, 8, 1, 9, 0),
        ),
        TitleEntity(
            code="sharp_shooter",
            label="슈팅이 매서운",
            category=TitleCategory.STRENGTH,
            granted_at=_at(2026, 8, 20, 12, 0),
        ),
    ],
)


# 생성 계약을 DB 없이 검사하려면 요청 사이에 남아야 한다. 저장소 인스턴스는 요청마다
# 새로 만들어지므로(프로바이더가 클래스 자체다) 모듈에 둔다.
_CREATED: dict[UUID, CardEntity] = {}


def reset_created_cards() -> None:
    """만들어 둔 카드를 비운다. **검사 사이에 상태가 새지 않게** 쓴다."""
    _CREATED.clear()


class StubCardRepository(CardPort):
    def find_by_owner(self, user_id: UUID) -> CardEntity | None:
        # 🔴 `_CREATED` 를 **먼저** 본다. 데모 카드를 먼저 돌려주면 수정이 반영되지
        #    않는다(`update_tagline` 이 여기에 복사해 둔다) — 고쳤는데 다시 읽으면
        #    옛 값이 나오는 상태가 된다.
        found = _CREATED.get(user_id)
        if found is not None:
            return found
        return _CARD if user_id == DEMO_USER_ID else None

    def find_by_slug(self, slug: PublicSlug) -> CardEntity | None:
        if slug == PublicSlug(DEMO_SLUG):
            return _CARD
        return next((c for c in _CREATED.values() if c.public_slug == slug), None)

    def update_tagline(self, user_id: UUID, tagline: str | None) -> CardEntity | None:
        """⚠️ **데모 카드(`_CARD`)는 모듈 상수라 안 바꾼다.** 바꾸면 다른 검사가
        보는 값이 실행 순서에 따라 달라진다 — 대신 `_CREATED` 로 복사해 둔다.
        """
        card = self.find_by_owner(user_id)
        if card is None:
            return None
        updated = replace(card, tagline=tagline)
        _CREATED[user_id] = updated
        return updated

    def create_for_owner(self, user_id: UUID) -> CardEntity:
        """멱등하게 만든다.

        ⚠️ **주인 닉네임을 모른다.** 스텁은 `user` 테이블을 읽지 않으므로(데모
        사용자만 이름을 안다) 고정 문자열을 넣는다. 닉네임이 실제로 `user` 에서
        읽히는지는 `tests/card/adapter/test_card_db.py` 가 본다.
        """
        existing = self.find_by_owner(user_id)
        if existing is not None:
            return existing

        card_id = uuid4()
        card = CardEntity(
            id=card_id,
            public_slug=PublicSlug.generate(),
            og_image_key=og_image_key_for(card_id),
            owner=CardOwner(id=user_id, nickname="스텁 사용자"),
            titles=[],
        )
        _CREATED[user_id] = card
        return card
