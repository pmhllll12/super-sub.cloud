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
    SquadCandidateFactsEntity,
    SquadRecruitmentFactsEntity,
    TeamPreferenceEntity,
)
from app.match.domain.rules.candidate_grade_rules import (
    display_grade,
    is_trust_dominant,
)
from app.match.domain.rules.match_preference_rules import overlap_minutes

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_team = table("team", column("id"), column("name"), column("region"))
_team_sport = table("team", column("id"), column("sport_code"))
_team_member = table(
    "team_member",
    column("team_id"),
    column("user_id"),
    column("role"),
    column("left_at"),
)
_user = table("user", column("id"), column("nickname"))
_position = table("position", column("id"))
_position_full = table(
    "position", column("id"), column("sport_code"), column("code")
)
_region = table(
    "region", column("id"), column("city"), column("district")
)
_squad = table("squad", column("id"), column("team_id"), column("formation"))
_squad_member = table("squad_member", column("squad_id"), column("player_card_id"))
_match = table("match", column("team_id"), column("played_at"))
# `card` 컨텍스트 — 스쿼드 등재는 카드 단위지 사람 단위가 아니라서 이걸 거쳐야
# 사람(user_id)이 나온다(`paik` 27번).
_player_card = table("player_card", column("id"), column("user_id"), column("public_slug"))
# `analysis` 컨텍스트 — 후보의 표시 등급(`paik` 25·26·27번). `find_card_grade`
# (`app/analysis/adapter/outbound/pg/video_pg_repository.py`)와 같은 조인이지만
# 컨텍스트끼리 임포트하지 않아서 복제한다.
_video = table(
    "video", column("id"), column("user_id"), column("is_featured"), column("created_at")
)
_analysis_job = table("analysis_job", column("id"), column("video_id"))
_analysis_metric = table(
    "analysis_metric", column("id"), column("analysis_job_id"), column("created_at")
)
_analysis_report = table(
    "analysis_report",
    column("analysis_metric_id"),
    column("overall_grade"),
    column("provisional"),
)
# `review` 컨텍스트 — 신뢰 축(재매칭 의사). `analysis`가 이미 하는 것과 같은
# 복제(위 파일의 grade_rules 절 참조).
_review = table("review", column("id"), column("reviewee_id"))
_review_selection = table(
    "review_selection", column("review_id"), column("option_code")
)
_TRUST_POSITIVE_CODE = "repeat_yes"
_TRUST_OPTION_CODES = (_TRUST_POSITIVE_CODE, "caution_would_not_repeat")


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

    # ── 빈 자리 후보 (paik 27번) ────────────────────────────────────

    def find_position(self, team_id: UUID, code: str) -> UUID | None:
        stmt = (
            select(_position_full.c.id)
            .select_from(
                _position_full.join(
                    _team_sport, _position_full.c.sport_code == _team_sport.c.sport_code
                )
            )
            .where(_team_sport.c.id == team_id, _position_full.c.code == code)
        )
        row = self._session.execute(stmt).first()
        return row[0] if row else None

    def squad_recruitment_facts(
        self, team_id: UUID, position_id: UUID
    ) -> SquadRecruitmentFactsEntity:
        squad_id = self._session.execute(
            select(_squad.c.id).where(_squad.c.team_id == team_id)
        ).scalar_one_or_none()

        # 하드 필터 1: 이미 이 스쿼드에 앉은 사람 (카드 → user_id).
        seated_user_ids: set[UUID] = set()
        if squad_id is not None:
            seated_user_ids = set(
                self._session.execute(
                    select(_player_card.c.user_id)
                    .select_from(
                        _squad_member.join(
                            _player_card,
                            _player_card.c.id == _squad_member.c.player_card_id,
                        )
                    )
                    .where(_squad_member.c.squad_id == squad_id)
                ).scalars()
            )

        # 하드 필터 2: 이 팀의 현재 소속(나간 사람은 이미 빠졌다).
        team_member_ids = set(
            self._session.execute(
                select(_team_member.c.user_id).where(
                    _team_member.c.team_id == team_id,
                    _team_member.c.left_at.is_(None),
                )
            ).scalars()
        )
        excluded = seated_user_ids | team_member_ids

        # 후보 원자료: 그 포지션을 등록했고 제외 대상이 아닌 사람.
        candidate_ids = set(
            self._session.execute(
                select(MemberMatchPositionOrm.user_id).where(
                    MemberMatchPositionOrm.position_id == position_id
                )
            ).scalars()
        ) - excluded

        # 하드 필터 3: 팀이 경기 시간을 등록해 뒀으면 그 시간과 겹치는 후보만
        # (팀이 안 등록했으면 이 필터는 건너뛴다 — `paik` 20번과 같은 완화).
        team_slots = self._session.execute(
            select(
                TeamMatchSlotOrm.weekday,
                TeamMatchSlotOrm.start_time,
                TeamMatchSlotOrm.end_time,
            ).where(TeamMatchSlotOrm.team_id == team_id)
        ).all()
        if team_slots and candidate_ids:
            member_slots = self._session.execute(
                select(
                    MemberMatchSlotOrm.user_id,
                    MemberMatchSlotOrm.weekday,
                    MemberMatchSlotOrm.start_time,
                    MemberMatchSlotOrm.end_time,
                ).where(MemberMatchSlotOrm.user_id.in_(candidate_ids))
            ).all()
            available: set[UUID] = set()
            for uid, weekday, start, end in member_slots:
                if uid in available:
                    continue
                for tw, ts, te in team_slots:
                    if overlap_minutes(weekday, start, end, tw, ts, te) > 0:
                        available.add(uid)
                        break
            candidate_ids &= available

        grades = self._grades_for(list(candidate_ids | seated_user_ids))
        seated_grades = [
            g for uid in seated_user_ids if (g := grades.get(uid, (None, None))[0])
        ]
        if not candidate_ids:
            return SquadRecruitmentFactsEntity(
                seated_grades=seated_grades, candidates=[]
            )

        nicknames = dict(
            self._session.execute(
                select(_user.c.id, _user.c.nickname).where(
                    _user.c.id.in_(candidate_ids)
                )
            ).all()
        )
        slugs = dict(
            self._session.execute(
                select(_player_card.c.user_id, _player_card.c.public_slug).where(
                    _player_card.c.user_id.in_(candidate_ids)
                )
            ).all()
        )
        last_active = dict(
            self._session.execute(
                select(_video.c.user_id, _video.c.created_at).where(
                    _video.c.user_id.in_(candidate_ids),
                    _video.c.is_featured.is_(True),
                )
            ).all()
        )

        candidates = [
            SquadCandidateFactsEntity(
                user_id=uid,
                nickname=nicknames.get(uid, ""),
                card_public_slug=slugs.get(uid),
                grade=grades.get(uid, (None, None))[0],
                provisional=grades.get(uid, (None, None))[1],
                last_active_at=last_active.get(uid),
            )
            for uid in candidate_ids
        ]
        return SquadRecruitmentFactsEntity(
            seated_grades=seated_grades, candidates=candidates
        )

    def _grades_for(
        self, user_ids: list[UUID]
    ) -> dict[UUID, tuple[str | None, bool | None]]:
        """`user_id` → (표시 등급, `provisional`). 대표 영상이 없거나 분석
        전이면 `(None, None)` — `analysis`의 `find_card_grade`와 같은 조인을
        복제한다(컨텍스트 경계, 위 테이블 정의 참조).
        """
        if not user_ids:
            return {}

        featured_video: dict[UUID, UUID] = dict(
            self._session.execute(
                select(_video.c.user_id, _video.c.id).where(
                    _video.c.user_id.in_(user_ids), _video.c.is_featured.is_(True)
                )
            ).all()
        )

        report_by_video: dict[UUID, tuple[str | None, bool | None]] = {}
        if featured_video:
            video_ids = list(featured_video.values())
            rows = self._session.execute(
                select(
                    _analysis_job.c.video_id,
                    _analysis_report.c.overall_grade,
                    _analysis_report.c.provisional,
                )
                .select_from(
                    _analysis_job.join(
                        _analysis_metric,
                        _analysis_metric.c.analysis_job_id == _analysis_job.c.id,
                    ).join(
                        _analysis_report,
                        _analysis_report.c.analysis_metric_id
                        == _analysis_metric.c.id,
                    )
                )
                .where(_analysis_job.c.video_id.in_(video_ids))
                .order_by(_analysis_metric.c.created_at.desc())
            ).all()
            for video_id, grade, provisional in rows:
                # 재분석은 여러 리포트를 남긴다 — DESC 순서라 먼저 만난 것이
                # 최신이다. `paik` 21번(임팩트 순간)과 같은 "먼저 만난 것이
                # 최신" 관례.
                report_by_video.setdefault(video_id, (grade, provisional))

        joined = _review.join(
            _review_selection, _review_selection.c.review_id == _review.c.id
        )
        totals = dict(
            self._session.execute(
                select(_review.c.reviewee_id, func.count(func.distinct(_review.c.id)))
                .select_from(joined)
                .where(
                    _review.c.reviewee_id.in_(user_ids),
                    _review_selection.c.option_code.in_(_TRUST_OPTION_CODES),
                )
                .group_by(_review.c.reviewee_id)
            ).all()
        )
        positives = dict(
            self._session.execute(
                select(_review.c.reviewee_id, func.count(func.distinct(_review.c.id)))
                .select_from(joined)
                .where(
                    _review.c.reviewee_id.in_(user_ids),
                    _review_selection.c.option_code == _TRUST_POSITIVE_CODE,
                )
                .group_by(_review.c.reviewee_id)
            ).all()
        )

        result: dict[UUID, tuple[str | None, bool | None]] = {}
        for uid in user_ids:
            video_id = featured_video.get(uid)
            overall_grade, provisional = (
                report_by_video.get(video_id, (None, None))
                if video_id is not None
                else (None, None)
            )
            trust_dominant = is_trust_dominant(positives.get(uid, 0), totals.get(uid, 0))
            result[uid] = (display_grade(overall_grade, trust_dominant), provisional)
        return result


def _required_headcount(formation: str) -> int:
    """`"5:5"` → 5. 형식이 다르면 앞 숫자만 읽고, 그마저 없으면 큰 수를 둬서
    "안 찬 것"으로 취급한다(방어적 — `squad.formation`은 앱이 아직 값 목록을
    DB로 강제하지 않는다, `paik` 9번 참고).
    """
    try:
        return int(formation.split(":")[0])
    except (ValueError, IndexError):
        return 999
