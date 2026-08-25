"""고정 응답 저장소.

DB가 없는 동안 `IdentityRepository` 자리를 채운다. **DB가 붙으면 이 파일을 지우고
`pg_repository.py`로 갈아끼운다** — 서비스와 라우터는 고치지 않는다.

에러 경로를 눌러볼 수 있어야 하므로 성공 조건을 좁게 잡았다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.identity.domain import Membership
from app.identity.service import User

DEMO_EMAIL = "demo@super-sub.example"
DEMO_PASSWORD = "supersub2026"

DEMO_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")

# 로그인이 내주는 토큰. 스텁이라 고정 문자열이고, DB 가 붙을 때 JWT 로 바뀐다.
# 만료 7일은 계약 문서 0장에서 정했다.
STUB_ACCESS_TOKEN = "stub-access-token-do-not-use-in-production"
TOKEN_EXPIRES_IN = 7 * 24 * 60 * 60

_ACTIVE_TEAM_ID = UUID("9a2e5f31-6d70-4c18-b3a9-4e82d7c05a16")
_LEFT_TEAM_ID = UUID("c4d17b02-8e35-4a91-b6f2-0d38e5a7c914")


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


_USER = User(
    id=DEMO_USER_ID,
    email=DEMO_EMAIL,
    nickname="홍길동",
    created_at=_at(2026, 7, 13, 10, 30),
)

# 나간 팀을 일부러 하나 넣어 둔다. 이게 있어야 active_memberships 가 실제로
# 무언가를 거르고, 거르지 않는 회귀가 테스트에 잡힌다.
_MEMBERSHIPS = [
    Membership(
        team_id=_ACTIVE_TEAM_ID,
        name="번개FC",
        region="서울 강남",
        sport_code="futsal",
        role="member",
        joined_at=_at(2026, 7, 1),
        left_at=None,
    ),
    Membership(
        team_id=_LEFT_TEAM_ID,
        name="옛날FC",
        region="서울 마포",
        sport_code="futsal",
        role="member",
        joined_at=_at(2026, 3, 1),
        left_at=_at(2026, 6, 30),
    ),
]


class StubIdentityRepository:
    def email_exists(self, email: str) -> bool:
        return email == DEMO_EMAIL

    def find_by_credentials(self, email: str, password: str) -> User | None:
        if email == DEMO_EMAIL and password == DEMO_PASSWORD:
            return _USER
        return None

    def get_user(self, user_id: UUID) -> User:
        return _USER

    def list_memberships(self, user_id: UUID) -> list[Membership]:
        return list(_MEMBERSHIPS)
