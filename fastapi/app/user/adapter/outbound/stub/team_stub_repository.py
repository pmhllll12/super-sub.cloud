"""메모리 저장소. **계약 테스트가 DB 없이 돌기 위한 것이다.**

동시성·유일 제약처럼 DB 만 답할 수 있는 것은 여기서 검사하지 않는다 —
`tests/user/adapter/test_team_db.py` 가 본다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.errors import ApiError
from app.user.application.ports.output.team_port import TeamPort
from app.user.domain.entities.team_entity import TeamEntity, TeamMemberEntity
from app.user.domain.value_objects.team_role_vo import TeamRole

# 마이그레이션이 넣는 값과 같다(`20260901_sport_and_position`).
SPORT_CODES = ("football", "baseball", "basketball")

_TEAMS: dict[UUID, TeamEntity] = {}
_MEMBERS: dict[UUID, list[TeamMemberEntity]] = {}
_KNOWN_USERS: set[UUID] = set()


def reset_teams() -> None:
    """검사 사이에 상태가 새지 않게 비운다."""
    _TEAMS.clear()
    _MEMBERS.clear()
    _KNOWN_USERS.clear()


def register_user(user_id: UUID) -> None:
    """스텁은 `user` 테이블이 없다. "이 사람은 있다"를 검사가 알려 준다."""
    _KNOWN_USERS.add(user_id)


class StubTeamRepository(TeamPort):
    def sport_exists(self, sport_code: str) -> bool:
        return sport_code in SPORT_CODES

    def user_exists(self, user_id: UUID) -> bool:
        return user_id in _KNOWN_USERS

    def find_team(self, team_id: UUID) -> TeamEntity | None:
        return _TEAMS.get(team_id)

    def active_members(self, team_id: UUID) -> list[TeamMemberEntity]:
        return list(_MEMBERS.get(team_id, []))

    def create_team(self, team: TeamEntity, owner_id: UUID) -> None:
        _TEAMS[team.id] = team
        _MEMBERS[team.id] = [self._member(owner_id, TeamRole.OWNER, 0)]
        _KNOWN_USERS.add(owner_id)

    def add_member(self, team_id: UUID, user_id: UUID) -> None:
        members = _MEMBERS.setdefault(team_id, [])
        if any(m.user_id == user_id for m in members):
            raise ApiError(409, "ALREADY_MEMBER", "이미 이 팀의 구성원입니다.")
        members.append(self._member(user_id, TeamRole.MEMBER, len(members)))

    def mark_left(self, team_id: UUID, user_id: UUID) -> None:
        _MEMBERS[team_id] = [
            m for m in _MEMBERS.get(team_id, []) if m.user_id != user_id
        ]

    def _member(self, user_id: UUID, role: TeamRole, order: int) -> TeamMemberEntity:
        # 가입 순서가 보이도록 시각을 벌린다. 같은 값이면 정렬 검사가 무의미해진다.
        return TeamMemberEntity(
            user_id=user_id,
            nickname="홍길동" if order == 0 else f"멤버{order}",
            role=role,
            joined_at=datetime(2026, 9, 1, tzinfo=timezone.utc)
            + timedelta(minutes=order),
        )
