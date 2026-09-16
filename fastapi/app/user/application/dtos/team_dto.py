"""팀 유스케이스가 주고받는 DTO. 값 객체가 아니라 **원시 타입**으로만 담는다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateTeamCommand:
    actor_id: UUID
    name: str
    region: str
    sport_code: str


@dataclass(frozen=True)
class TeamQuery:
    actor_id: UUID
    team_id: UUID


@dataclass(frozen=True)
class UpdateTeamCommand:
    """팀 이름·지역 수정.

    `None` 이면 **안 건드린다**(HTTP 층에서 「안 보냄」이 여기로 온다).
    🔴 `sport_code` 는 담지 않는다 — 포지션·스쿼드·경기가 전부 그 값에
    매달려 있어서, 바꾸면 이미 앉힌 포지션이 다른 종목 것이 된다.
    받을 자리를 아예 안 두는 것이 그 규칙을 코드로 지키는 방법이다
    (카드가 `public_slug` 를 안 받는 것과 같은 판단).
    """

    actor_id: UUID
    team_id: UUID
    name: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class JoinTeamCommand:
    actor_id: UUID
    team_id: UUID
    # None 이면 본인이 가입하는 것이다. 값이 있으면 `owner` 가 남을 넣는 것이다.
    user_id: UUID | None = None


@dataclass(frozen=True)
class LeaveTeamCommand:
    actor_id: UUID
    team_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class TeamMemberResult:
    user_id: UUID
    nickname: str
    role: str
    joined_at: datetime
    # 카드가 없는 구성원은 둘 다 None 이다. 자세한 이유는 `TeamMemberEntity`.
    player_card_id: UUID | None = None
    card_public_slug: str | None = None


@dataclass(frozen=True)
class TeamResult:
    id: UUID
    name: str
    region: str
    sport_code: str
    members: list[TeamMemberResult] = field(default_factory=list)


@dataclass(frozen=True)
class CreateTeamInvitationCommand:
    actor_id: UUID
    team_id: UUID
    invited_user_id: UUID


@dataclass(frozen=True)
class RespondTeamInvitationCommand:
    actor_id: UUID
    invitation_id: UUID


@dataclass(frozen=True)
class CancelTeamInvitationCommand:
    actor_id: UUID
    team_id: UUID
    invitation_id: UUID


@dataclass(frozen=True)
class TeamInvitationsQuery:
    """팀이 보낸 초대 목록(주장만) — `GET /teams/{id}/invitations`."""

    actor_id: UUID
    team_id: UUID


@dataclass(frozen=True)
class MyTeamInvitationsQuery:
    """내가 받은, 아직 답 안 한 초대 목록 — `GET /me/invitations`."""

    user_id: UUID


@dataclass(frozen=True)
class TeamInvitationResult:
    id: UUID
    team_id: UUID
    invited_user_id: UUID
    status: str
    created_at: datetime
    responded_at: datetime | None
