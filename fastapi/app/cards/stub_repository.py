"""고정 응답 저장소. DB가 붙으면 이 파일을 지우고 pg 구현으로 갈아끼운다."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.cards.domain import Card, CardOwner, Title
from app.identity.stub_repository import DEMO_USER_ID

DEMO_SLUG = "hong-gildong-4f2a"

_CARD_ID = UUID("7b4d1a08-5c39-4e62-8f77-91ac3e0d4b25")


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


_CARD = Card(
    id=_CARD_ID,
    public_slug=DEMO_SLUG,
    og_image_key=f"cards/{_CARD_ID}.png",
    owner=CardOwner(id=DEMO_USER_ID, nickname="홍길동"),
    titles=[
        # 일부러 오래된 것을 먼저 둔다. visible_titles 가 최신 순으로 정렬하는지
        # 테스트에서 확인하려면 입력이 정렬돼 있으면 안 된다.
        Title(
            code="weekend_regular",
            label="주말 개근",
            category="활동",
            granted_at=_at(2026, 8, 1, 9, 0),
        ),
        Title(
            code="sharp_shooter",
            label="슈팅이 매서운",
            category="강점",
            granted_at=_at(2026, 8, 20, 12, 0),
        ),
    ],
)


class StubCardRepository:
    def find_by_user(self, user_id: UUID) -> Card | None:
        return _CARD if user_id == DEMO_USER_ID else None

    def find_by_slug(self, public_slug: str) -> Card | None:
        return _CARD if public_slug == DEMO_SLUG else None
