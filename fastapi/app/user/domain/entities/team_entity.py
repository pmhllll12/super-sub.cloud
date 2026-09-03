"""`team` 과 그 구성원. 부록 D 도메인 ①."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.user.domain.value_objects.team_role_vo import TeamRole


@dataclass(frozen=True)
class TeamEntity:
    """팀 1개.

    **종목은 팀이 정한다**(5장 SFR-010) — 경기에 종목 컬럼을 따로 두지 않고
    `match -> team -> sport_code` 로 결정된다(부록 D.4).
    """

    id: UUID
    name: str
    region: str
    sport_code: str


@dataclass(frozen=True)
class TeamMemberEntity:
    """지금 소속된 구성원 1명.

    나간 사람은 여기 담지 않는다 — `team_member` 는 `left_at` 으로 소프트 삭제라
    거르는 것은 도메인 규칙의 몫이다(`membership_rules.active_memberships` 와 같은 결).
    """

    user_id: UUID
    nickname: str
    role: TeamRole
    joined_at: datetime
