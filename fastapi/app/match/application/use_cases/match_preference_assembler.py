"""엔티티 ↔ DTO 변환 + `paik` 20번 소프트 점수 조립.

정렬·근거 문장은 **여기서** 만든다(`domain/rules/match_preference_rules.py`의
순수 함수를 부른다) — 저장소는 원자료만 준다. 부록D 정규화 원칙과 같은 이유로
점수 자체는 어디에도 저장하지 않는다(파생값).
"""

from __future__ import annotations

from app.match.application.dtos.match_preference_dto import (
    MatchCandidateResult,
    MatchReasonResult,
    MemberPreferenceResult,
    MemberPreferenceSummaryResult,
    SlotInput,
    SquadCandidateResult,
    TeamPreferenceResult,
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
from app.match.domain.rules.candidate_grade_rules import skill_value
from app.match.domain.rules.match_preference_rules import (
    overlap_minutes,
    region_tier,
)


def to_slot_entities(slots: list[SlotInput]) -> list[SlotEntity]:
    return [SlotEntity(s.weekday, s.start_time, s.end_time) for s in slots]


def _to_slot_inputs(slots: list[SlotEntity]) -> list[SlotInput]:
    return [SlotInput(s.weekday, s.start_time, s.end_time) for s in slots]


def to_team_preference_result(pref: TeamPreferenceEntity) -> TeamPreferenceResult:
    return TeamPreferenceResult(
        team_id=pref.team_id,
        region_ids=pref.region_ids,
        slots=_to_slot_inputs(pref.slots),
    )


def to_member_preference_result(
    pref: MemberPreferenceEntity,
) -> MemberPreferenceResult:
    return MemberPreferenceResult(
        user_id=pref.user_id,
        region_ids=pref.region_ids,
        slots=_to_slot_inputs(pref.slots),
        position_ids=pref.position_ids,
    )


def to_member_preference_summary_result(
    m: MemberPreferenceSummaryEntity,
) -> MemberPreferenceSummaryResult:
    return MemberPreferenceSummaryResult(
        user_id=m.user_id,
        nickname=m.nickname,
        region_ids=m.region_ids,
        slots=_to_slot_inputs(m.slots),
        position_ids=m.position_ids,
    )


def _weekday_label(weekday: int) -> str:
    return ["월", "화", "수", "목", "금", "토", "일"][weekday]


def _time_reasons(
    our_slots: list[SlotEntity], their_slots: list[SlotEntity]
) -> tuple[int, list[str]]:
    """총 겹치는 분 + 근거 문장들. `paik` 20번 — "구체적일수록 안전하다"라
    "토요일 10:00~12:00 겹침" 처럼 실제 겹친 구간을 그대로 적는다.
    """
    total = 0
    reasons: list[str] = []
    for ours in our_slots:
        for theirs in their_slots:
            minutes = overlap_minutes(
                ours.weekday,
                ours.start_time,
                ours.end_time,
                theirs.weekday,
                theirs.start_time,
                theirs.end_time,
            )
            if minutes <= 0:
                continue
            total += minutes
            start = max(ours.start_time, theirs.start_time)
            end = min(ours.end_time, theirs.end_time)
            reasons.append(
                f"{_weekday_label(ours.weekday)}요일 "
                f"{start.strftime('%H:%M')}~{end.strftime('%H:%M')} 겹침"
            )
    return total, reasons


def _best_region_tier(
    our_regions: list[RegionFactEntity], their_regions: list[RegionFactEntity]
) -> tuple[str, str | None]:
    """우리 선호 지역과 상대 선호 지역 중 **가장 가까운 조합**. 근거 문장에
    실제 어느 지역이 겹쳤는지 적는다(막연한 "지역이 맞음"이 아니라).
    """
    best = "none"
    best_pair: tuple[RegionFactEntity, RegionFactEntity] | None = None
    for ours in our_regions:
        for theirs in their_regions:
            tier = region_tier(ours.city, ours.district, theirs.city, theirs.district)
            if tier == "district":
                return "district", f"같은 구({theirs.city} {theirs.district})"
            if tier == "city" and best != "city":
                best = "city"
                best_pair = (ours, theirs)
    if best == "city" and best_pair is not None:
        return "city", f"같은 시({best_pair[1].city})"
    return "none", None


# 소프트 근거 무게 — 정상호 회신 "시작값이 필요하면 시간 > 지역을 권한다"
# (장소는 옮길 수 있어도 시간은 못 옮긴다).
_TIME_WEIGHT = 2
_REGION_WEIGHT = 1
_REGION_TIER_SCORE = {"district": 2, "city": 1, "none": 0}


def to_candidate_result(
    our_slots: list[SlotEntity],
    our_regions: list[RegionFactEntity],
    facts: list[CandidateFactsEntity],
) -> list[MatchCandidateResult]:
    rows: list[tuple[float, float, MatchCandidateResult]] = []
    for f in facts:
        minutes, time_reasons = _time_reasons(our_slots, f.slots)
        tier, region_reason = _best_region_tier(our_regions, f.regions)

        reasons: list[MatchReasonResult] = [
            MatchReasonResult(kind="time", detail=r) for r in time_reasons
        ]
        if region_reason:
            reasons.append(MatchReasonResult(kind="region", detail=region_reason))

        score = minutes * _TIME_WEIGHT + _REGION_TIER_SCORE[tier] * _REGION_WEIGHT
        recency = f.last_active_at.timestamp() if f.last_active_at else 0.0
        rows.append(
            (
                score,
                recency,
                MatchCandidateResult(
                    team_id=f.team_id,
                    team_name=f.team_name,
                    region_label=f.region_label,
                    formation=f.formation,
                    reasons=reasons,
                ),
            )
        )

    # 소프트 근거 0개(score 0)인 팀은 뒤로 몰되, 그 안에서도 최근 활동순
    # (죽은 팀이 위로 안 오게 — `paik` 20번 정상호 회신).
    rows.sort(key=lambda row: (row[0] <= 0, -row[0], -row[1]))
    return [row[2] for row in rows]


def _to_squad_candidate_result(c: SquadCandidateFactsEntity) -> SquadCandidateResult:
    return SquadCandidateResult(
        user_id=c.user_id,
        nickname=c.nickname,
        card_public_slug=c.card_public_slug,
        grade=c.grade,
        provisional=c.provisional,
    )


def _average_skill(seated_grades: list[str]) -> float | None:
    """이미 앉은 사람들의 실력 축 평균. 등급 없는 사람은 셈에서 뺀다
    (`ho` 21번과 같은 판단) — 아무도 등급이 없으면 `None`."""
    values = [v for g in seated_grades if (v := skill_value(g)) is not None]
    if not values:
        return None
    return sum(values) / len(values)


def to_squad_candidate_results(
    facts: SquadRecruitmentFactsEntity, wanted_grade: str | None
) -> list[SquadCandidateResult]:
    """`paik` 27번. `wanted_grade`가 있으면(사용자가 직접 고른 칸) 그 칸으로
    **하드 필터**하고 최근 활동순만 매긴다. 없으면 **거르지 않고** 팀 평균과의
    실력 축 거리로 정렬한다(정상호 회신 — 기본값은 거르지 말고 정렬하길
    권함). 🔴 거리·점수는 정렬에만 쓰고 응답에는 안 싣는다(20번과 같은 원칙).
    """

    def _recency(c: SquadCandidateFactsEntity) -> float:
        return c.last_active_at.timestamp() if c.last_active_at else 0.0

    if wanted_grade is not None:
        chosen = [c for c in facts.candidates if c.grade == wanted_grade]
        chosen.sort(key=lambda c: -_recency(c))
        return [_to_squad_candidate_result(c) for c in chosen]

    team_avg = _average_skill(facts.seated_grades)
    rows: list[tuple[bool, float, float, SquadCandidateFactsEntity]] = []
    for c in facts.candidates:
        value = skill_value(c.grade)
        no_grade = value is None
        # 🔴 「등급을 모르는 사람」은 거리 축에 안 올린다 — 모르는 값에 자리를
        # 주면 안 잰 것이 근거가 된다(`ho` 21번). 뒤로 보내고, 그 안에서는
        # 최근 활동순으로만 가른다.
        distance = 0.0 if (no_grade or team_avg is None) else abs(value - team_avg)
        rows.append((no_grade, distance, _recency(c), c))
    rows.sort(key=lambda row: (row[0], row[1], -row[2]))
    return [_to_squad_candidate_result(row[3]) for row in rows]
