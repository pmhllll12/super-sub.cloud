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
