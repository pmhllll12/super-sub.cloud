"""엔티티 → DTO 변환. **여기까지가 도메인의 마지막 지점이다.**"""

from __future__ import annotations

from app.match.application.dtos.match_dto import (
    ApplicationResult,
    MatchListingResult,
    MatchResult,
    PositionNeedResult,
)
from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.entities.match_entity import MatchEntity, MatchListingEntity


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


def to_listing_result(listing: MatchListingEntity) -> MatchListingResult:
    """탐색 한 줄. 팀 값을 **평평하게** 펴서 내보낸다."""
    match = listing.match
    return MatchListingResult(
        id=match.id,
        team_id=match.team_id,
        team_name=listing.team_name,
        region=listing.region,
        sport_code=listing.sport_code,
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


def to_application_result(application: ApplicationEntity) -> ApplicationResult:
    """`confirmed` 는 저장된 값이 아니라 **두 시각에서 계산된다**(부록 D.5).

    클라이언트가 두 시각을 보고 스스로 판단하게 두면 확정 조건이 화면마다 갈린다.
    """
    return ApplicationResult(
        id=application.id,
        match_id=application.match_id,
        user_id=application.user_id,
        nickname=application.nickname,
        team_accepted_at=application.team_accepted_at,
        user_accepted_at=application.user_accepted_at,
        confirmed=application.is_confirmed,
    )

