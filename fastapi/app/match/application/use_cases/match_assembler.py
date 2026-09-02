"""엔티티 → DTO 변환. **여기까지가 도메인의 마지막 지점이다.**"""

from __future__ import annotations

from app.match.application.dtos.match_dto import MatchResult, PositionNeedResult
from app.match.domain.entities.match_entity import MatchEntity


def to_match_result(match: MatchEntity) -> MatchResult:
    return MatchResult(
        id=match.id,
        team_id=match.team_id,
        played_at=match.played_at,
        place=match.place,
        needs=[
            PositionNeedResult(
                position_code=n.code,
                position_label=n.label,
                head_count=n.head_count,
            )
            for n in match.needs
        ],
    )
