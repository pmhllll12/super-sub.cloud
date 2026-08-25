"""내 정보 유스케이스가 주고받는 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class MeQuery:
    user_id: UUID


@dataclass(frozen=True)
class MembershipResult:
    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: datetime


@dataclass(frozen=True)
class MeResult:
    id: UUID
    email: str
    nickname: str
    created_at: datetime
    # 지금 소속된 팀만. 거르는 규칙은 domain/rules/membership_rules.py 에 있다.
    teams: list[MembershipResult] = field(default_factory=list)
