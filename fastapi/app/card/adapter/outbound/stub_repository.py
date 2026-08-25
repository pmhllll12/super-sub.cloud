"""고정 데이터 저장소. DB 가 붙으면 지우고 `pg_repository.py` 로 갈아끼운다.

> ⚠️ **이 파일만 `user` 컨텍스트를 임포트한다.** 데모 카드의 주인을 데모 사용자와
> 맞추기 위해서다. 컨텍스트끼리 직접 얽히면 안 되지만 **스텁끼리의 임포트라 둘 다
> DB 가 붙는 순간 함께 사라진다.** 도메인·유스케이스·라우터에는 이 의존이 없다 —
> `find_by_owner` 가 `user_id` 를 인자로 받기 때문이다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.card.domain.entities import Card, CardOwner, Title
from app.card.domain.value_objects import PublicSlug, TitleCategory
from app.user.adapter.outbound.stub_repository import DEMO_USER_ID

DEMO_SLUG = "hong-gildong-4f2a"

_CARD_ID = UUID("7b4d1a08-5c39-4e62-8f77-91ac3e0d4b25")


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


_CARD = Card(
    id=_CARD_ID,
    public_slug=PublicSlug(DEMO_SLUG),
    og_image_key=f"cards/{_CARD_ID}.png",
    owner=CardOwner(id=DEMO_USER_ID, nickname="홍길동"),
    titles=[
        # 일부러 오래된 것을 먼저 둔다. visible_titles 가 최신 순으로 정렬하는지
        # 확인하려면 입력이 정렬돼 있으면 안 된다.
        Title(
            code="weekend_regular",
            label="주말 개근",
            category=TitleCategory.ACTIVITY,
            granted_at=_at(2026, 8, 1, 9, 0),
        ),
        Title(
            code="sharp_shooter",
            label="슈팅이 매서운",
            category=TitleCategory.STRENGTH,
            granted_at=_at(2026, 8, 20, 12, 0),
        ),
    ],
)


class StubCardRepository:
    def find_by_owner(self, user_id: UUID) -> Card | None:
        return _CARD if user_id == DEMO_USER_ID else None

    def find_by_slug(self, slug: PublicSlug) -> Card | None:
        return _CARD if slug == PublicSlug(DEMO_SLUG) else None
