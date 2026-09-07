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
# user_id -> (player_card_id, public_slug). 실물은 `player_card` 를 outerjoin 해서
# 얻는다 — **없는 사람이 있다**는 것이 요점이라 딕셔너리로 흉내 낸다.
_CARDS: dict[UUID, tuple[UUID, str]] = {}


def reset_teams() -> None:
    """검사 사이에 상태가 새지 않게 비운다."""
    _TEAMS.clear()
    _MEMBERS.clear()
    _KNOWN_USERS.clear()
    _CARDS.clear()


def register_card(user_id: UUID, card_id: UUID, public_slug: str) -> None:
    """"이 사람은 카드가 있다"를 검사가 알려 준다.

    🔴 **`add_member` 보다 먼저 부른다.** 구성원을 만들 때 카드 값을 읽어 담기
    때문이다 — 실물은 조회 시점에 조인하므로 순서가 상관없지만, 스텁은 만들 때
    한 번 담는다. 이 차이가 드러나는 검사는 `test_team_db.py` 쪽이다.
    """
    _CARDS[user_id] = (card_id, public_slug)


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
        card = _CARDS.get(user_id)
        return TeamMemberEntity(
            user_id=user_id,
            nickname="홍길동" if order == 0 else f"멤버{order}",
            role=role,
            joined_at=datetime(2026, 9, 1, tzinfo=timezone.utc)
            + timedelta(minutes=order),
            player_card_id=card[0] if card else None,
            card_public_slug=card[1] if card else None,
        )
