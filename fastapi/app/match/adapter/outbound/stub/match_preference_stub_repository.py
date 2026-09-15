"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다. `paik` 18·20·21번.

`team`·`team_member`·`squad`·`position`·`region`을 이 스텁은 모른다(원시
쿼리로만 읽는 실물처럼) — 검사가 `register_*` 함수로 필요한 사실을 알려 준다.

🔴 **`user` 스텁(`region_stub_repository`)을 임포트하지 않는다** — 컨텍스트
경계 검사(`tests/test_architecture.py`)가 스텁이라고 봐주지 않는다. 그래서
지역 픽스처를 여기 따로 둔다(실물과 id 값은 안 같아도 된다, 계약 테스트는
형태만 본다).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.match.application.ports.output.match_preference_port import (
    MatchPreferencePort,
)
from app.match.domain.entities.match_preference_entity import (
    CandidateFactsEntity,
    MemberPreferenceEntity,
    MemberPreferenceSummaryEntity,
    RegionFactEntity,
    SlotEntity,
    TeamPreferenceEntity,
)

# 계약 테스트용 지역 픽스처 — 같은 시 안에 구가 둘(계층 검증용).
REGIONS_BY_ID: dict[UUID, RegionFactEntity] = {
    uuid4(): RegionFactEntity(city="서울", district="강남구"),
    uuid4(): RegionFactEntity(city="서울", district="서초구"),
    uuid4(): RegionFactEntity(city="서울", district="마포구"),
    uuid4(): RegionFactEntity(city="경기", district="수원시"),
    uuid4(): RegionFactEntity(city="부산", district="해운대구"),
}

_TEAMS: dict[UUID, dict] = {}  # team_id -> {"name":..., "region":...}
_MEMBERSHIPS: dict[tuple[UUID, UUID], str] = {}  # (team_id, user_id) -> role
_NICKNAMES: dict[UUID, str] = {}
_SQUADS: dict[UUID, dict] = {}  # team_id -> {"formation":..., "roster": int}
_POSITIONS: set[UUID] = set()
_LAST_MATCH: dict[UUID, datetime] = {}

_TEAM_REGIONS: dict[UUID, list[UUID]] = {}
_TEAM_SLOTS: dict[UUID, list[SlotEntity]] = {}
_MEMBER_REGIONS: dict[UUID, list[UUID]] = {}
_MEMBER_SLOTS: dict[UUID, list[SlotEntity]] = {}
_MEMBER_POSITIONS: dict[UUID, list[UUID]] = {}


def reset_match_preferences() -> None:
    for d in (
        _TEAMS,
        _MEMBERSHIPS,
        _NICKNAMES,
        _SQUADS,
        _POSITIONS,
        _LAST_MATCH,
        _TEAM_REGIONS,
        _TEAM_SLOTS,
        _MEMBER_REGIONS,
        _MEMBER_SLOTS,
        _MEMBER_POSITIONS,
    ):
        d.clear()


def register_team(team_id: UUID, name: str = "팀", region: str = "서울 강남구") -> None:
    _TEAMS[team_id] = {"name": name, "region": region}


def register_team_member(
    team_id: UUID, user_id: UUID, role: str, nickname: str
) -> None:
    _MEMBERSHIPS[(team_id, user_id)] = role
    _NICKNAMES[user_id] = nickname


def register_squad(team_id: UUID, formation: str, roster: int) -> None:
    _SQUADS[team_id] = {"formation": formation, "roster": roster}


def register_position(position_id: UUID) -> None:
    _POSITIONS.add(position_id)


def register_last_match(team_id: UUID, played_at: datetime) -> None:
    _LAST_MATCH[team_id] = played_at


class StubMatchPreferenceRepository(MatchPreferencePort):
    def team_exists(self, team_id: UUID) -> bool:
        return team_id in _TEAMS

    def team_role(self, team_id: UUID, user_id: UUID) -> str | None:
        return _MEMBERSHIPS.get((team_id, user_id))

    def region_ids_exist(self, region_ids: list[UUID]) -> bool:
        return all(r in REGIONS_BY_ID for r in region_ids)

    def position_ids_exist(self, position_ids: list[UUID]) -> bool:
        return all(p in _POSITIONS for p in position_ids)

    def team_formation(self, team_id: UUID) -> str | None:
        squad = _SQUADS.get(team_id)
        return squad["formation"] if squad else None

    def resolve_regions(self, region_ids: list[UUID]) -> list[RegionFactEntity]:
        return [REGIONS_BY_ID[r] for r in region_ids if r in REGIONS_BY_ID]

    def set_team_preference(
        self, team_id: UUID, region_ids: list[UUID], slots: list[SlotEntity]
    ) -> TeamPreferenceEntity:
        _TEAM_REGIONS[team_id] = list(region_ids)
        _TEAM_SLOTS[team_id] = list(slots)
        return self.get_team_preference(team_id)

    def get_team_preference(self, team_id: UUID) -> TeamPreferenceEntity:
        return TeamPreferenceEntity(
            team_id=team_id,
            region_ids=_TEAM_REGIONS.get(team_id, []),
            slots=_TEAM_SLOTS.get(team_id, []),
        )

    def set_member_preference(
        self,
        user_id: UUID,
        region_ids: list[UUID],
        slots: list[SlotEntity],
        position_ids: list[UUID],
    ) -> MemberPreferenceEntity:
        _MEMBER_REGIONS[user_id] = list(region_ids)
        _MEMBER_SLOTS[user_id] = list(slots)
        _MEMBER_POSITIONS[user_id] = list(position_ids)
        return self.get_member_preference(user_id)

    def get_member_preference(self, user_id: UUID) -> MemberPreferenceEntity:
        return MemberPreferenceEntity(
            user_id=user_id,
            region_ids=_MEMBER_REGIONS.get(user_id, []),
            slots=_MEMBER_SLOTS.get(user_id, []),
            position_ids=_MEMBER_POSITIONS.get(user_id, []),
        )

    def list_member_preferences_for_team(
        self, team_id: UUID
    ) -> list[MemberPreferenceSummaryEntity]:
        out = []
        for (tid, uid), _role in _MEMBERSHIPS.items():
            if tid != team_id:
                continue
            pref = self.get_member_preference(uid)
            out.append(
                MemberPreferenceSummaryEntity(
                    user_id=uid,
                    nickname=_NICKNAMES.get(uid, ""),
                    region_ids=pref.region_ids,
                    slots=pref.slots,
                    position_ids=pref.position_ids,
                )
            )
        return out

    def list_candidate_facts(
        self, team_id: UUID, formation: str | None
    ) -> list[CandidateFactsEntity]:
        if formation is None:
            return []
        required = int(formation.split(":")[0]) if ":" in formation else 999
        out = []
        for tid, squad in _SQUADS.items():
            if tid == team_id or squad["formation"] != formation:
                continue
            if squad["roster"] < required:
                continue
            regions = _TEAM_REGIONS.get(tid, [])
            slots = _TEAM_SLOTS.get(tid, [])
            if not regions and not slots:
                continue
            team = _TEAMS.get(tid, {"name": "", "region": ""})
            out.append(
                CandidateFactsEntity(
                    team_id=tid,
                    team_name=team["name"],
                    region_label=team["region"],
                    formation=formation,
                    regions=self.resolve_regions(regions),
                    slots=list(slots),
                    last_active_at=_LAST_MATCH.get(tid),
                )
            )
        return out
