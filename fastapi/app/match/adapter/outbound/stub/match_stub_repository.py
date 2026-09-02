"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다.

포지션 목록은 마이그레이션(`20260902_match_tables`)이 넣는 값과 같다. 여기서
갈리면 스텁으로는 통과하고 실물에서 깨진다.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.match.application.ports.output.match_port import MatchPort
from app.match.domain.entities.match_entity import MatchEntity, PositionNeedEntity

_POSITIONS = {
    "football": {"GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"},
    "baseball": {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"},
    "basketball": {"G": "가드", "F": "포워드", "C": "센터"},
}

_TEAMS: dict[UUID, str] = {}
_ROLES: dict[tuple[UUID, UUID], str] = {}
_MATCHES: dict[UUID, MatchEntity] = {}


def reset_matches() -> None:
    _TEAMS.clear()
    _ROLES.clear()
    _MATCHES.clear()


def register_team(team_id: UUID, sport_code: str) -> None:
    """스텁에는 `team` 테이블이 없다. 검사가 "이 팀은 이 종목"이라고 알려 준다."""
    _TEAMS[team_id] = sport_code


def register_role(team_id: UUID, user_id: UUID, role: str) -> None:
    _ROLES[(team_id, user_id)] = role


class StubMatchRepository(MatchPort):
    def team_exists(self, team_id: UUID) -> bool:
        return team_id in _TEAMS

    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        return _ROLES.get((team_id, user_id))

    def find_positions(
        self, team_id: UUID, codes: list[str]
    ) -> dict[str, PositionNeedEntity]:
        labels = _POSITIONS.get(_TEAMS.get(team_id, ""), {})
        return {
            code: PositionNeedEntity(
                position_id=uuid4(), code=code, label=labels[code], head_count=0
            )
            for code in codes
            if code in labels
        }

    def create_match(self, match: MatchEntity) -> None:
        _MATCHES[match.id] = match

    def find_match(self, match_id: UUID) -> MatchEntity | None:
        return _MATCHES.get(match_id)
