"""고정 데이터 저장소.

DB 가 없는 동안 `UserRepository` 자리를 채운다. **DB 가 붙으면 이 파일을 지우고
`pg_repository.py` 로 갈아끼운다** — 유스케이스·라우터는 고치지 않는다.

에러 경로를 눌러볼 수 있어야 하므로 성공 조건을 좁게 잡았다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.user.domain.entities import Membership, User
from app.user.domain.value_objects import Email, Nickname, Password

DEMO_EMAIL = "demo@super-sub.example"
DEMO_PASSWORD = "supersub2026"
DEMO_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")

_ACTIVE_TEAM_ID = UUID("9a2e5f31-6d70-4c18-b3a9-4e82d7c05a16")
_LEFT_TEAM_ID = UUID("c4d17b02-8e35-4a91-b6f2-0d38e5a7c914")


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


_USER = User(
    id=DEMO_USER_ID,
    email=Email.of(DEMO_EMAIL),
    nickname=Nickname.of("홍길동"),
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


class StubUserRepository:
    def email_exists(self, email: Email) -> bool:
        return email == Email.of(DEMO_EMAIL)

    def find_by_credentials(self, email: Email, password: Password) -> User | None:
        if email == Email.of(DEMO_EMAIL) and password.value == DEMO_PASSWORD:
            return _USER
        return None

    def get(self, user_id: UUID) -> User | None:
        return _USER if user_id == DEMO_USER_ID else None

    def list_memberships(self, user_id: UUID) -> list[Membership]:
        return list(_MEMBERSHIPS)
