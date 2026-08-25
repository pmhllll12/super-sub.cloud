"""출력 포트.

유스케이스가 **저장소의 구현을 모르게** 하는 경계다. 지금은 스텁이 이 자리에
들어가고 DB 가 생기면 PostgreSQL 구현이 들어간다 — 유스케이스는 고치지 않는다.

ABC 가 아니라 `Protocol` 을 쓴다. 구현체가 이 파일을 임포트하지 않아도 되므로
의존 방향이 한쪽으로만 흐른다.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.user.domain.entities import Membership, User
from app.user.domain.value_objects import Email, Password


class UserRepository(Protocol):
    def email_exists(self, email: Email) -> bool: ...

    def find_by_credentials(self, email: Email, password: Password) -> User | None: ...

    def get(self, user_id: UUID) -> User | None: ...

    def list_memberships(self, user_id: UUID) -> list[Membership]: ...
