"""엔티티 → DTO 변환. **여기까지가 도메인의 마지막 지점이다.**"""

from __future__ import annotations

from app.user.application.dtos.team_dto import TeamMemberResult, TeamResult
from app.user.domain.entities.team_entity import TeamEntity, TeamMemberEntity


def to_team_result(
    team: TeamEntity, members: list[TeamMemberEntity]
) -> TeamResult:
    return TeamResult(
        id=team.id,
        name=team.name,
        region=team.region,
        sport_code=team.sport_code,
        members=[
            TeamMemberResult(
                user_id=m.user_id,
                nickname=m.nickname,
                role=str(m.role),
                joined_at=m.joined_at,
                player_card_id=m.player_card_id,
                card_public_slug=m.card_public_slug,
            )
            for m in members
        ],
    )
