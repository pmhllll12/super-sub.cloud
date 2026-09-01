"""관리자용 회원 관리 유스케이스가 주고받는 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ListUsersQuery:
    q: str | None
    page: int
    size: int


@dataclass(frozen=True)
class AdminUserSummary:
    id: UUID
    email: str
    nickname: str
    created_at: datetime


@dataclass(frozen=True)
class ListUsersResult:
    items: list[AdminUserSummary]
    total: int
    page: int
    size: int


@dataclass(frozen=True)
class AdminMembershipResult:
    """`MembershipResult`(me_dto.py)와 달리 `left_at` 을 그대로 들고 있다.

    관리자는 나간 팀도 봐야 하므로 `active_memberships` 로 거르지 않는다.
    """

    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: datetime
    left_at: datetime | None


@dataclass(frozen=True)
class AdminUserDetailQuery:
    user_id: UUID


@dataclass(frozen=True)
class AdminUserDetailResult:
    id: UUID
    email: str
    nickname: str
    created_at: datetime
    teams: list[AdminMembershipResult] = field(default_factory=list)
    has_card: bool = False


@dataclass(frozen=True)
class ForceDeleteUserCommand:
    user_id: UUID
    # 되돌릴 수 없는 동작이라 **누가 눌렀는지**를 감사 로그에 남긴다. 지워진 사람만
    # 남으면 사후에 추적할 수 없다 (5장 SEC-010).
    admin_id: UUID
