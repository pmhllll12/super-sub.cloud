"""지인 신청·검색 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


# 지인 검색 개수 상한 — 페이지네이션 없이 이걸로 전수 스크래핑을 막는다.
SEARCH_LIMIT = 20


@dataclass(frozen=True)
class SearchUsersQuery:
    actor_id: UUID
    q: str


@dataclass(frozen=True)
class UserSearchResult:
    id: UUID
    nickname: str


@dataclass(frozen=True)
class RequestContactCommand:
    requester_id: UUID
    target_id: UUID
    note: str | None = None


@dataclass(frozen=True)
class AcceptContactCommand:
    actor_id: UUID
    contact_id: UUID


@dataclass(frozen=True)
class ListContactsQuery:
    user_id: UUID


@dataclass(frozen=True)
class ListContactRequestsQuery:
    user_id: UUID


@dataclass(frozen=True)
class ContactResult:
    id: UUID
    requester_user_id: UUID
    target_user_id: UUID
    note: str | None
    accepted_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class ContactSummaryResult:
    contact_id: UUID
    user_id: UUID
    nickname: str
    note: str | None
    accepted_at: datetime


@dataclass(frozen=True)
class ContactListResult:
    items: list[ContactSummaryResult] = field(default_factory=list)
