"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다.

포지션 목록은 마이그레이션(`20260902_match_tables`)이 넣는 값과 같다. 여기서
갈리면 스텁으로는 통과하고 실물에서 깨진다.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from app.card.application.ports.output.squad_port import SquadPort
from app.card.domain.entities.squad_entity import SquadEntity, SquadMemberEntity
from app.card.domain.value_objects.public_slug_vo import PublicSlug

_POSITIONS = {
    "football": {"GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"},
    "baseball": {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"},
    "basketball": {"G": "가드", "F": "포워드", "C": "센터"},
}

_TEAMS: dict[UUID, str] = {}
_ROLES: dict[tuple[UUID, UUID], str] = {}
_SQUADS: dict[UUID, SquadEntity] = {}
# 카드 id -> (주인 user_id, 카드 슬러그, 닉네임). 스텁에는 `player_card` 가 없다.
_CARDS: dict[UUID, tuple[UUID, str, str]] = {}
# 포지션 코드마다 안정된 id 를 준다 — 같은 코드면 같은 id 여야 한다.
_POSITION_IDS: dict[tuple[str, str], UUID] = {}


def reset_squads() -> None:
    _TEAMS.clear()
    _ROLES.clear()
    _SQUADS.clear()
    _CARDS.clear()
    _POSITION_IDS.clear()


def register_team(team_id: UUID, sport_code: str) -> None:
    """스텁에는 `team` 테이블이 없다. 검사가 "이 팀은 이 종목"이라고 알려 준다."""
    _TEAMS[team_id] = sport_code


def register_role(team_id: UUID, user_id: UUID, role: str) -> None:
    _ROLES[(team_id, user_id)] = role


def register_card(card_id: UUID, owner_id: UUID, nickname: str = "선수") -> None:
    """스텁에는 `player_card` 가 없다. 검사가 "이 카드는 이 사람 것"이라고 알려 준다."""
    _CARDS[card_id] = (owner_id, f"slug-{card_id.hex[:8]}", nickname)


class StubSquadRepository(SquadPort):
    def team_exists(self, team_id: UUID) -> bool:
        return team_id in _TEAMS

    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        return _ROLES.get((team_id, user_id))

    def find_by_team(self, team_id: UUID) -> SquadEntity | None:
        return next((s for s in _SQUADS.values() if s.team_id == team_id), None)

    def find_by_slug(self, public_slug: str) -> SquadEntity | None:
        return next(
            (s for s in _SQUADS.values() if str(s.public_slug) == public_slug), None
        )

    def create_for_team(self, team_id: UUID) -> tuple[SquadEntity, bool]:
        existing = self.find_by_team(team_id)
        if existing is not None:
            return existing, False
        squad = SquadEntity(
            id=uuid4(), team_id=team_id, public_slug=PublicSlug.generate()
        )
        _SQUADS[squad.id] = squad
        return squad, True

    def find_position(self, team_id: UUID, code: str) -> tuple[UUID, str] | None:
        sport = _TEAMS.get(team_id)
        if sport is None:
            return None
        label = _POSITIONS.get(sport, {}).get(code)
        if label is None:
            return None
        key = (sport, code)
        _POSITION_IDS.setdefault(key, uuid4())
        return _POSITION_IDS[key], label

    def card_owner(self, player_card_id: UUID) -> UUID | None:
        found = _CARDS.get(player_card_id)
        return None if found is None else found[0]

    def enlist(
        self, squad_id: UUID, player_card_id: UUID, position_id: UUID
    ) -> SquadMemberEntity:
        squad = _SQUADS[squad_id]
        if any(m.player_card_id == player_card_id for m in squad.members):
            # 실물의 유일 제약과 같은 신호를 낸다. 인터랙터가 409 로 바꾼다.
            raise ValueError("이미 등재된 카드다")

        _, card_slug, nickname = _CARDS[player_card_id]
        code, label = self._position_of(position_id)
        member = SquadMemberEntity(
            id=uuid4(),
            player_card_id=player_card_id,
            card_public_slug=card_slug,
            nickname=nickname,
            position_id=position_id,
            position_code=code,
            position_label=label,
        )
        _SQUADS[squad_id] = replace(squad, members=[*squad.members, member])
        return member

    def find_member(self, member_id: UUID) -> tuple[UUID, UUID] | None:
        for squad in _SQUADS.values():
            for member in squad.members:
                if member.id == member_id:
                    return squad.id, member.player_card_id
        return None

    def discharge(self, member_id: UUID) -> None:
        for squad_id, squad in _SQUADS.items():
            remaining = [m for m in squad.members if m.id != member_id]
            if len(remaining) != len(squad.members):
                _SQUADS[squad_id] = replace(squad, members=remaining)
                return

    def _position_of(self, position_id: UUID) -> tuple[str, str]:
        for (sport, code), pid in _POSITION_IDS.items():
            if pid == position_id:
                return code, _POSITIONS[sport][code]
        raise KeyError(position_id)
