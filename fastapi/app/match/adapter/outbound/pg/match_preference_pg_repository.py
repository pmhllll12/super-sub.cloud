"""`MatchPreferencePort`의 PostgreSQL 구현. `paik` 18·20·21번.

🔴 **`user`·`card` 컨텍스트를 임포트하지 않는다.** 팀·팀원·스쿼드·포지션·지역이
전부 남의 테이블이라 `table()`/`column()` 원시 쿼리로만 읽는다 — `match_pg_
repository.py`와 같은 방식이다.

⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 파이썬이 안 잡아 준다.
`tests/match/adapter/test_match_preference_db.py`가 유일한 방어선이다.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import column, delete, func, select, table
from sqlalchemy.orm import Session

from app.match.adapter.outbound.orm.member_match_position_orm import (
    MemberMatchPositionOrm,
)
from app.match.adapter.outbound.orm.member_match_region_orm import (
    MemberMatchRegionOrm,
)
from app.match.adapter.outbound.orm.member_match_slot_orm import MemberMatchSlotOrm
from app.match.adapter.outbound.orm.team_match_region_orm import TeamMatchRegionOrm
from app.match.adapter.outbound.orm.team_match_slot_orm import TeamMatchSlotOrm
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

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_team = table("team", column("id"), column("name"), column("region"))
_team_member = table(
    "team_member",
    column("team_id"),
    column("user_id"),
    column("role"),
    column("left_at"),
)
_user = table("user", column("id"), column("nickname"))
_position = table("position", column("id"))
_region = table(
    "region", column("id"), column("city"), column("district")
)
_squad = table("squad", column("id"), column("team_id"), column("formation"))
_squad_member = table("squad_member", column("squad_id"), column("player_card_id"))
_match = table("match", column("team_id"), column("played_at"))


class MatchPreferencePgRepository(MatchPreferencePort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def team_exists(self, team_id: UUID) -> bool:
        stmt = select(_team.c.id).where(_team.c.id == team_id)
        return self._session.execute(stmt).first() is not None

    def team_role(self, team_id: UUID, user_id: UUID) -> str | None:
        stmt = select(_team_member.c.role).where(
            _team_member.c.team_id == team_id,
            _team_member.c.user_id == user_id,
            _team_member.c.left_at.is_(None),
        )
        row = self._session.execute(stmt).first()
        return row[0] if row else None

    def region_ids_exist(self, region_ids: list[UUID]) -> bool:
        if not region_ids:
            return True
        found = self._session.execute(
            select(func.count()).where(_region.c.id.in_(region_ids))
        ).scalar_one()
        return found == len(set(region_ids))

    def position_ids_exist(self, position_ids: list[UUID]) -> bool:
        if not position_ids:
            return True
        found = self._session.execute(
            select(func.count()).where(_position.c.id.in_(position_ids))
        ).scalar_one()
        return found == len(set(position_ids))

    def resolve_regions(self, region_ids: list[UUID]) -> list[RegionFactEntity]:
        if not region_ids:
            return []
        rows = self._session.execute(
            select(_region.c.city, _region.c.district).where(
                _region.c.id.in_(region_ids)
            )
        ).all()
        return [RegionFactEntity(city=r[0], district=r[1]) for r in rows]

    def team_formation(self, team_id: UUID) -> str | None:
        row = self._session.execute(
            select(_squad.c.formation).where(_squad.c.team_id == team_id)
        ).first()
        return row[0] if row else None

    # ── 팀 조건 ──────────────────────────────────────────────────────

    def set_team_preference(
        self, team_id: UUID, region_ids: list[UUID], slots: list[SlotEntity]
    ) -> TeamPreferenceEntity:
        self._session.execute(
            delete(TeamMatchRegionOrm).where(TeamMatchRegionOrm.team_id == team_id)
        )
        self._session.execute(
            delete(TeamMatchSlotOrm).where(TeamMatchSlotOrm.team_id == team_id)
        )
        for rid in region_ids:
            self._session.add(
                TeamMatchRegionOrm(id=uuid4(), team_id=team_id, region_id=rid)
            )
        for s in slots:
            self._session.add(
                TeamMatchSlotOrm(
                    id=uuid4(),
                    team_id=team_id,
                    weekday=s.weekday,
                    start_time=s.start_time,
                    end_time=s.end_time,
                )
            )
        self._session.commit()
        return self.get_team_preference(team_id)

    def get_team_preference(self, team_id: UUID) -> TeamPreferenceEntity:
        region_ids = [
            r[0]
            for r in self._session.execute(
                select(TeamMatchRegionOrm.region_id).where(
                    TeamMatchRegionOrm.team_id == team_id
                )
            ).all()
        ]
        slots = [
            SlotEntity(weekday=r[0], start_time=r[1], end_time=r[2])
            for r in self._session.execute(
                select(
                    TeamMatchSlotOrm.weekday,
                    TeamMatchSlotOrm.start_time,
                    TeamMatchSlotOrm.end_time,
                ).where(TeamMatchSlotOrm.team_id == team_id)
            ).all()
        ]
        return TeamPreferenceEntity(
            team_id=team_id, region_ids=region_ids, slots=slots
        )

    # ── 개인 조건 ────────────────────────────────────────────────────

    def set_member_preference(
        self,
        user_id: UUID,
        region_ids: list[UUID],
        slots: list[SlotEntity],
        position_ids: list[UUID],
    ) -> MemberPreferenceEntity:
        self._session.execute(
            delete(MemberMatchRegionOrm).where(
                MemberMatchRegionOrm.user_id == user_id
            )
        )
        self._session.execute(
            delete(MemberMatchSlotOrm).where(MemberMatchSlotOrm.user_id == user_id)
        )
        self._session.execute(
            delete(MemberMatchPositionOrm).where(
                MemberMatchPositionOrm.user_id == user_id
            )
        )
        for rid in region_ids:
            self._session.add(
                MemberMatchRegionOrm(id=uuid4(), user_id=user_id, region_id=rid)
            )
        for s in slots:
            self._session.add(
                MemberMatchSlotOrm(
                    id=uuid4(),
                    user_id=user_id,
                    weekday=s.weekday,
                    start_time=s.start_time,
                    end_time=s.end_time,
                )
            )
        for pid in position_ids:
            self._session.add(
                MemberMatchPositionOrm(
                    id=uuid4(), user_id=user_id, position_id=pid
                )
            )
        self._session.commit()
        return self.get_member_preference(user_id)

    def get_member_preference(self, user_id: UUID) -> MemberPreferenceEntity:
        region_ids = [
            r[0]
            for r in self._session.execute(
                select(MemberMatchRegionOrm.region_id).where(
                    MemberMatchRegionOrm.user_id == user_id
                )
            ).all()
        ]
        slots = [
            SlotEntity(weekday=r[0], start_time=r[1], end_time=r[2])
            for r in self._session.execute(
                select(
                    MemberMatchSlotOrm.weekday,
                    MemberMatchSlotOrm.start_time,
                    MemberMatchSlotOrm.end_time,
                ).where(MemberMatchSlotOrm.user_id == user_id)
            ).all()
        ]
        position_ids = [
            r[0]
            for r in self._session.execute(
                select(MemberMatchPositionOrm.position_id).where(
                    MemberMatchPositionOrm.user_id == user_id
                )
            ).all()
        ]
        return MemberPreferenceEntity(
            user_id=user_id,
            region_ids=region_ids,
            slots=slots,
            position_ids=position_ids,
        )

    def list_member_preferences_for_team(
        self, team_id: UUID
    ) -> list[MemberPreferenceSummaryEntity]:
        members = self._session.execute(
            select(_team_member.c.user_id, _user.c.nickname)
            .select_from(_team_member.join(_user, _user.c.id == _team_member.c.user_id))
            .where(
                _team_member.c.team_id == team_id,
                _team_member.c.left_at.is_(None),
            )
        ).all()
        results = []
        for user_id, nickname in members:
            pref = self.get_member_preference(user_id)
            results.append(
                MemberPreferenceSummaryEntity(
                    user_id=user_id,
                    nickname=nickname,
                    region_ids=pref.region_ids,
                    slots=pref.slots,
                    position_ids=pref.position_ids,
                )
            )
        return results

    # ── 후보 (paik 20번) ────────────────────────────────────────────

    def list_candidate_facts(
        self, team_id: UUID, formation: str | None
    ) -> list[CandidateFactsEntity]:
        if formation is None:
            return []

        # 하드 필터 1: 같은 formation의 스쿼드를 가진, 자기 팀이 아닌 팀.
        candidate_team_ids = [
            r[0]
            for r in self._session.execute(
                select(_squad.c.team_id).where(
                    _squad.c.formation == formation, _squad.c.team_id != team_id
                )
            ).all()
        ]
        if not candidate_team_ids:
            return []

        # 하드 필터 2: 로스터가 formation 인원만큼 찼음(예: "5:5" → 5명).
        required = _required_headcount(formation)
        squad_id_by_team = dict(
            self._session.execute(
                select(_squad.c.team_id, _squad.c.id).where(
                    _squad.c.team_id.in_(candidate_team_ids)
                )
            ).all()
        )
        counts = self._session.execute(
            select(_squad_member.c.squad_id, func.count())
            .where(_squad_member.c.squad_id.in_(squad_id_by_team.values()))
            .group_by(_squad_member.c.squad_id)
        ).all()
        count_by_squad = dict(counts)
        full_team_ids = [
            tid
            for tid, sid in squad_id_by_team.items()
            if count_by_squad.get(sid, 0) >= required
        ]
        if not full_team_ids:
            return []

        # 하드 필터 3: 경기 조건(지역 또는 시간)을 하나라도 등록한 팀만.
        teams_with_region = {
            r[0]
            for r in self._session.execute(
                select(TeamMatchRegionOrm.team_id).where(
                    TeamMatchRegionOrm.team_id.in_(full_team_ids)
                )
            ).all()
        }
        teams_with_slot = {
            r[0]
            for r in self._session.execute(
                select(TeamMatchSlotOrm.team_id).where(
                    TeamMatchSlotOrm.team_id.in_(full_team_ids)
                )
            ).all()
        }
        eligible_ids = list(teams_with_region | teams_with_slot)
        if not eligible_ids:
            return []

        teams = self._session.execute(
            select(_team.c.id, _team.c.name, _team.c.region).where(
                _team.c.id.in_(eligible_ids)
            )
        ).all()

        # 최근 활동 — 그 팀이 주최한 가장 최근 경기 시각(정렬 꼬리용, 정보 없으면 None).
        last_match = dict(
            self._session.execute(
                select(_match.c.team_id, func.max(_match.c.played_at))
                .where(_match.c.team_id.in_(eligible_ids))
                .group_by(_match.c.team_id)
            ).all()
        )

        results = []
        for tid, name, region_label in teams:
            region_rows = self._session.execute(
                select(_region.c.city, _region.c.district)
                .select_from(
                    TeamMatchRegionOrm.__table__.join(
                        _region, _region.c.id == TeamMatchRegionOrm.region_id
                    )
                )
                .where(TeamMatchRegionOrm.team_id == tid)
            ).all()
            slot_rows = self._session.execute(
                select(
                    TeamMatchSlotOrm.weekday,
                    TeamMatchSlotOrm.start_time,
                    TeamMatchSlotOrm.end_time,
                ).where(TeamMatchSlotOrm.team_id == tid)
            ).all()
            results.append(
                CandidateFactsEntity(
                    team_id=tid,
                    team_name=name,
                    region_label=region_label,
                    formation=formation,
                    regions=[
                        RegionFactEntity(city=c, district=d) for c, d in region_rows
                    ],
                    slots=[
                        SlotEntity(weekday=w, start_time=s, end_time=e)
                        for w, s, e in slot_rows
                    ],
                    last_active_at=last_match.get(tid),
                )
            )
        return results


def _required_headcount(formation: str) -> int:
    """`"5:5"` → 5. 형식이 다르면 앞 숫자만 읽고, 그마저 없으면 큰 수를 둬서
    "안 찬 것"으로 취급한다(방어적 — `squad.formation`은 앱이 아직 값 목록을
    DB로 강제하지 않는다, `paik` 9번 참고).
    """
    try:
        return int(formation.split(":")[0])
    except (ValueError, IndexError):
        return 999
