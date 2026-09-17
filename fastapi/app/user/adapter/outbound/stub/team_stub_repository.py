"""메모리 저장소. **계약 테스트가 DB 없이 돌기 위한 것이다.**

동시성·유일 제약처럼 DB 만 답할 수 있는 것은 여기서 검사하지 않는다 —
`tests/user/adapter/test_team_db.py` 가 본다.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.user.application.ports.output.team_port import TeamPort
from app.user.domain.entities.team_entity import (
    MyTeamInvitationEntity,
    TeamEntity,
    TeamInvitationEntity,
    TeamMemberEntity,
)
from app.user.domain.rules.team_invitation_rules import PENDING
from app.user.domain.value_objects.team_role_vo import TeamRole

# 마이그레이션이 넣는 값과 같다(`20260901_sport_and_position`).
SPORT_CODES = ("football", "baseball", "basketball")
# 지금 새로 받는 종목(`sport.active`, `ho` 39번). 나머지는 행만 남아 있다.
ACTIVE_SPORT_CODES = ("football",)

_TEAMS: dict[UUID, TeamEntity] = {}
_MEMBERS: dict[UUID, list[TeamMemberEntity]] = {}
_KNOWN_USERS: set[UUID] = set()
# user_id -> (player_card_id, public_slug). 실물은 `player_card` 를 outerjoin 해서
# 얻는다 — **없는 사람이 있다**는 것이 요점이라 딕셔너리로 흉내 낸다.
_CARDS: dict[UUID, tuple[UUID, str]] = {}
_INVITATIONS: dict[UUID, TeamInvitationEntity] = {}
# team_id -> 스쿼드 공개 슬러그. 스텁에는 `squad` 테이블이 없다 —
# **없는 팀이 있다**는 것이 요점이라(`_CARDS` 와 같은 이유) 딕셔너리로 흉내 낸다.
_SQUAD_SLUGS: dict[UUID, str] = {}
# 앞으로 있을 경기가 있는 팀(`paik` 35번). 스텁에는 `match` 테이블이 없다.
_UPCOMING_MATCHES: set[UUID] = set()
# 포지션 목록은 마이그레이션(`20260902_match_tables`)이 넣는 값과 같다.
_POSITIONS = {
    "football": {"GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"},
    "baseball": {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"},
    "basketball": {"G": "가드", "F": "포워드", "C": "센터"},
}
# 같은 (종목, 약칭)이면 같은 id 여야 한다 — `squad_stub_repository` 와 같은 방식.
_POSITION_IDS: dict[tuple[str, str], UUID] = {}


def reset_teams() -> None:
    """검사 사이에 상태가 새지 않게 비운다."""
    _TEAMS.clear()
    _MEMBERS.clear()
    _KNOWN_USERS.clear()
    _CARDS.clear()
    _INVITATIONS.clear()
    _SQUAD_SLUGS.clear()
    _POSITION_IDS.clear()
    _UPCOMING_MATCHES.clear()


def register_card(user_id: UUID, card_id: UUID, public_slug: str) -> None:
    """"이 사람은 카드가 있다"를 검사가 알려 준다.

    🔴 **`add_member` 보다 먼저 부른다.** 구성원을 만들 때 카드 값을 읽어 담기
    때문이다 — 실물은 조회 시점에 조인하므로 순서가 상관없지만, 스텁은 만들 때
    한 번 담는다. 이 차이가 드러나는 검사는 `test_team_db.py` 쪽이다.
    """
    _CARDS[user_id] = (card_id, public_slug)


def register_squad(team_id: UUID, public_slug: str) -> None:
    """"이 팀은 스쿼드가 있다"를 검사가 알려 준다(`paik` 37번).

    안 부르면 그 팀 초대의 `squad_public_slug` 가 `None` 이다 — 실물에서도
    스쿼드를 아직 안 만든 팀이 그렇다.
    """
    _SQUAD_SLUGS[team_id] = public_slug


def register_upcoming_match(team_id: UUID) -> None:
    """"이 팀은 앞으로 있을 경기가 있다"를 검사가 알려 준다(`paik` 35번)."""
    _UPCOMING_MATCHES.add(team_id)


def register_user(user_id: UUID) -> None:
    """스텁은 `user` 테이블이 없다. "이 사람은 있다"를 검사가 알려 준다."""
    _KNOWN_USERS.add(user_id)


class StubTeamRepository(TeamPort):
    def sport_exists(self, sport_code: str) -> bool:
        return sport_code in SPORT_CODES

    def sport_is_active(self, sport_code: str) -> bool:
        return sport_code in ACTIVE_SPORT_CODES

    def user_exists(self, user_id: UUID) -> bool:
        return user_id in _KNOWN_USERS

    def find_team(self, team_id: UUID) -> TeamEntity | None:
        return _TEAMS.get(team_id)

    def update_team(
        self, team_id: UUID, name: str | None, region: str | None
    ) -> TeamEntity | None:
        team = _TEAMS.get(team_id)
        if team is None:
            return None
        updated = replace(
            team,
            name=team.name if name is None else name,
            region=team.region if region is None else region,
        )
        _TEAMS[team_id] = updated
        return updated

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

    def set_member_role(self, team_id: UUID, user_id: UUID, role: str) -> None:
        _MEMBERS[team_id] = [
            replace(m, role=TeamRole(role)) if m.user_id == user_id else m
            for m in _MEMBERS.get(team_id, [])
        ]

    # --- 팀 해체 (`paik` 35번). `match` 쪽 정리는 흉내 내지 않는다 —
    #     실제 DB 검사가 본다(알림 생성과 같은 판단). ------------------------

    def has_upcoming_match(self, team_id: UUID) -> bool:
        """스텁에는 `match` 가 없다. 검사가 `register_upcoming_match` 로 알려 준다."""
        return team_id in _UPCOMING_MATCHES

    def disband_team(self, team_id: UUID) -> None:
        team = _TEAMS.get(team_id)
        if team is not None:
            _TEAMS[team_id] = replace(team, disbanded_at=datetime.now(timezone.utc))
        _MEMBERS[team_id] = []
        for key, invitation in list(_INVITATIONS.items()):
            if invitation.team_id == team_id and invitation.status == PENDING:
                _INVITATIONS[key] = replace(
                    invitation,
                    status="cancelled",
                    responded_at=datetime.now(timezone.utc),
                )

    # --- 팀 초대 (`min` 20번). 알림 생성은 흉내 내지 않는다 — 실제 DB 검사가
    #     본다(`test_team_match_request_db.py`와 같은 판단). --------------------

    def create_team_invitation(self, invitation: TeamInvitationEntity) -> None:
        _INVITATIONS[invitation.id] = invitation

    def find_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity | None:
        return _INVITATIONS.get(invitation_id)

    def find_pending_invitation(
        self, team_id: UUID, invited_user_id: UUID
    ) -> TeamInvitationEntity | None:
        return next(
            (
                i
                for i in _INVITATIONS.values()
                if i.team_id == team_id
                and i.invited_user_id == invited_user_id
                and i.status == PENDING
            ),
            None,
        )

    def list_team_invitations(self, team_id: UUID) -> list[TeamInvitationEntity]:
        items = [i for i in _INVITATIONS.values() if i.team_id == team_id]
        return sorted(items, key=lambda i: i.created_at, reverse=True)

    def list_my_pending_invitations(
        self, user_id: UUID
    ) -> list[MyTeamInvitationEntity]:
        items = [
            i
            for i in _INVITATIONS.values()
            if i.invited_user_id == user_id and i.status == PENDING
        ]
        return [
            MyTeamInvitationEntity(
                invitation=i,
                team_name=_TEAMS[i.team_id].name,
                team_region=_TEAMS[i.team_id].region,
                team_sport_code=_TEAMS[i.team_id].sport_code,
                squad_public_slug=_SQUAD_SLUGS.get(i.team_id),
            )
            for i in sorted(items, key=lambda i: i.created_at, reverse=True)
        ]

    def find_position(self, sport_code: str, code: str) -> tuple[UUID, str] | None:
        label = _POSITIONS.get(sport_code, {}).get(code)
        if label is None:
            return None
        _POSITION_IDS.setdefault((sport_code, code), uuid4())
        return _POSITION_IDS[(sport_code, code)], label

    def accept_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        return self._respond(invitation_id, "accepted")

    def reject_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        return self._respond(invitation_id, "rejected")

    def cancel_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        return self._respond(invitation_id, "cancelled")

    def _respond(self, invitation_id: UUID, status: str) -> TeamInvitationEntity:
        updated = replace(
            _INVITATIONS[invitation_id],
            status=status,
            responded_at=datetime.now(timezone.utc),
        )
        _INVITATIONS[invitation_id] = updated
        return updated

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
