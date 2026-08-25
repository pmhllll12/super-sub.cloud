"""사용자·팀 유스케이스.

라우터(HTTP)와 리포지터리(저장소) 사이에 있다. **여기서는 저장소의 구현을 모른다** —
`IdentityRepository` 프로토콜만 안다. 지금은 스텁이 그 자리에 들어가고 DB가 생기면
PostgreSQL 구현으로 갈아끼운다. 그게 이 계층을 둔 이유다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from app.errors import ApiError
from app.identity.domain import Membership, active_memberships, normalize_email


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    nickname: str
    created_at: datetime


class IdentityRepository(Protocol):
    """출력 포트. 구현은 `stub_repository.py`, 나중에 `pg_repository.py`."""

    def email_exists(self, email: str) -> bool: ...

    def find_by_credentials(self, email: str, password: str) -> User | None: ...

    def get_user(self, user_id: UUID) -> User: ...

    def list_memberships(self, user_id: UUID) -> list[Membership]: ...


class IdentityService:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repo = repository

    def signup(self, email: str, password: str, nickname: str) -> User:
        normalized = normalize_email(email)
        if self._repo.email_exists(normalized):
            raise ApiError(409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다.")

        # 스텁 단계라 저장하지 않는다. 비밀번호도 아직 해싱하지 않는다 —
        # 저장할 곳이 없기 때문이고, DB 가 붙을 때 bcrypt 를 넣는다.
        return User(
            id=uuid4(),
            email=normalized,
            nickname=nickname.strip(),
            created_at=datetime.now(timezone.utc),
        )

    def login(self, email: str, password: str) -> User:
        user = self._repo.find_by_credentials(normalize_email(email), password)
        if user is None:
            # 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다 —
            # 구분하면 가입 여부가 새어 나간다(계약 문서 2장).
            raise ApiError(
                401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다."
            )
        return user

    def me(self, user_id: UUID) -> tuple[User, list[Membership]]:
        user = self._repo.get_user(user_id)
        memberships = active_memberships(self._repo.list_memberships(user_id))
        return user, memberships
