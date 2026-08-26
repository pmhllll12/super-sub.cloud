"""고정 데이터 저장소.

DB 가 없는 동안 `UserPort` 자리를 채운다. **DB 가 붙으면 이 파일 옆에
`user_pg_repository.py` 를 만들고 프로바이더 한 줄만 바꾼다.**

지금은 ORM 이 없어서 `mappers/` 도 없다. PostgreSQL 구현이 들어올 때
`adapter/outbound/orm/user_orm.py` 와 `adapter/outbound/mappers/user_mapper.py`
가 함께 생긴다 — 그때 ORM 행을 엔티티로 바꾸는 일이 매퍼의 몫이다.

에러 경로를 눌러볼 수 있어야 하므로 성공 조건을 좁게 잡았다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.user.application.ports.output.user_port import UserPort
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname
from app.user.domain.value_objects.password_vo import Password

DEMO_EMAIL = "demo@super-sub.example"
DEMO_PASSWORD = "supersub2026"
DEMO_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")

_ACTIVE_TEAM_ID = UUID("9a2e5f31-6d70-4c18-b3a9-4e82d7c05a16")
_LEFT_TEAM_ID = UUID("c4d17b02-8e35-4a91-b6f2-0d38e5a7c914")


def _at(y: int, mo: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


_USER = UserEntity(
    id=DEMO_USER_ID,
    email=Email.of(DEMO_EMAIL),
    nickname=Nickname.of("홍길동"),
    created_at=_at(2026, 7, 13, 10, 30),
)

# 나간 팀을 일부러 하나 넣어 둔다. 이게 있어야 active_memberships 가 실제로
# 무언가를 거르고, 거르지 않는 회귀가 테스트에 잡힌다.
_MEMBERSHIPS = [
    MembershipEntity(
        team_id=_ACTIVE_TEAM_ID,
        name="번개FC",
        region="서울 강남",
        sport_code="futsal",
        role="member",
        joined_at=_at(2026, 7, 1),
        left_at=None,
    ),
    MembershipEntity(
        team_id=_LEFT_TEAM_ID,
        name="옛날FC",
        region="서울 마포",
        sport_code="futsal",
        role="member",
        joined_at=_at(2026, 3, 1),
        left_at=_at(2026, 6, 30),
    ),
]


class StubUserRepository(UserPort):
    def email_exists(self, email: Email) -> bool:
        return email == Email.of(DEMO_EMAIL)

    def create(self, user: UserEntity, password: Password) -> None:
        """스텁은 고정 데이터라 저장하지 않는다.

        가입 응답 형태를 확인하는 데는 이걸로 충분하다. **실제로 저장되는지는
        DB 를 붙인 테스트(`tests/user/adapter/test_auth_db.py`)가 검사한다.**
        """

    def find_by_credentials(
        self, email: Email, password: Password
    ) -> UserEntity | None:
        if email == Email.of(DEMO_EMAIL) and password.value == DEMO_PASSWORD:
            return _USER
        return None

    def find_by_identity(self, provider: str, subject: str) -> UserEntity | None:
        """스텁에는 연결된 외부 계정이 없다. 항상 "처음 온 사람"으로 답한다."""
        return None

    def find_by_email(self, email: Email) -> UserEntity | None:
        return _USER if email == Email.of(DEMO_EMAIL) else None

    def link_identity(self, user_id: UUID, provider: str, subject: str) -> None:
        """스텁은 저장하지 않는다."""

    def create_with_identity(
        self, user: UserEntity, provider: str, subject: str
    ) -> None:
        """스텁은 저장하지 않는다."""

    def get(self, user_id: UUID) -> UserEntity | None:
        return _USER if user_id == DEMO_USER_ID else None

    def update_nickname(self, user_id: UUID, nickname: Nickname) -> None:
        """스텁은 고정 데이터라 저장하지 않는다.

        응답 형태 확인에는 충분하다 — 실제로 반영되는지는 DB 테스트가 본다.
        """

    def list_memberships(self, user_id: UUID) -> list[MembershipEntity]:
        return list(_MEMBERSHIPS)
