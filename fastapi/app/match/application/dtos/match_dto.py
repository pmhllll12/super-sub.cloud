"""경기 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PositionNeedInput:
    position_code: str
    head_count: int


@dataclass(frozen=True)
class CreateMatchCommand:
    actor_id: UUID
    team_id: UUID
    played_at: datetime
    place: str
    needs: list[PositionNeedInput]


@dataclass(frozen=True)
class TeamMatchesQuery:
    team_id: UUID


@dataclass(frozen=True)
class MatchQuery:
    match_id: UUID


@dataclass(frozen=True)
class PositionNeedResult:
    position_code: str
    position_label: str
    head_count: int


@dataclass(frozen=True)
class MatchResult:
    id: UUID
    team_id: UUID
    played_at: datetime
    place: str
    needs: list[PositionNeedResult] = field(default_factory=list)
@dataclass(frozen=True)
class ApplyCommand:
    actor_id: UUID
    match_id: UUID
    # None 이면 본인이 지원한다. 값이 있으면 주장이 그 사람에게 제안한다.
    user_id: UUID | None = None


@dataclass(frozen=True)
class AcceptApplicationCommand:
    actor_id: UUID
    match_id: UUID
    application_id: UUID


@dataclass(frozen=True)
class ApplicationsQuery:
    actor_id: UUID
    match_id: UUID


@dataclass(frozen=True)
class ApplicationResult:
    id: UUID
    match_id: UUID
    user_id: UUID
    nickname: str
    team_accepted_at: datetime | None
    user_accepted_at: datetime | None
    confirmed: bool
