"""스쿼드 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class CreateSquadCommand:
    actor_id: UUID
    team_id: UUID


@dataclass(frozen=True)
class TeamSquadQuery:
    actor_id: UUID
    team_id: UUID


@dataclass(frozen=True)
class PublicSquadQuery:
    """공개 조회. **인증하지 않으므로 `actor_id` 가 없다**(SFR-009 와 같은 결)."""

    public_slug: str


@dataclass(frozen=True)
class EnlistCardCommand:
    actor_id: UUID
    team_id: UUID
    player_card_id: UUID
    position_code: str


@dataclass(frozen=True)
class DischargeMemberCommand:
    actor_id: UUID
    team_id: UUID
    member_id: UUID


@dataclass(frozen=True)
class SquadMemberResult:
    id: UUID
    player_card_id: UUID
    card_public_slug: str
    nickname: str
    position_code: str
    position_label: str


@dataclass(frozen=True)
class SquadResult:
    id: UUID
    team_id: UUID
    public_slug: str
    members: list[SquadMemberResult] = field(default_factory=list)


@dataclass(frozen=True)
class SquadCreation:
    """만들었는지 이미 있었는지를 함께 돌려준다.

    라우터가 201 과 200 을 가르는 데 쓴다 — `POST /me/card` 와 같은 방식이다.
    """

    squad: SquadResult
    created: bool
