"""경기 조건·후보 라우터. 계약 문서. `paik` 18·20·21번."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserId
from app.match.adapter.inbound.api.schemas.match_preference_schema import (
    MatchCandidateResponse,
    MemberPreferenceResponse,
    MemberPreferenceSummaryResponse,
    SetMemberPreferenceSchema,
    SetTeamPreferenceSchema,
    SquadCandidateResponse,
    TeamPreferenceResponse,
)
from app.match.application.dtos.match_preference_dto import (
    GetMemberPreferenceQuery,
    GetTeamPreferenceQuery,
    ListMatchCandidatesQuery,
    ListMemberPreferencesQuery,
    ListSquadCandidatesQuery,
    MatchCandidateResult,
    MemberPreferenceResult,
    MemberPreferenceSummaryResult,
    SetMemberPreferenceCommand,
    SetTeamPreferenceCommand,
    SlotInput,
    SquadCandidateResult,
    TeamPreferenceResult,
)
from app.match.dependencies.match_preference_providers import (
    GetMemberPreferenceUseCaseDep,
    GetTeamPreferenceUseCaseDep,
    ListMatchCandidatesUseCaseDep,
    ListMemberPreferencesUseCaseDep,
    ListSquadCandidatesUseCaseDep,
    SetMemberPreferenceUseCaseDep,
    SetTeamPreferenceUseCaseDep,
)

match_preference_router = APIRouter(tags=["match-preferences"])


@match_preference_router.put(
    "/teams/{team_id}/match-preferences", response_model=TeamPreferenceResponse
)
def set_team_preference(
    team_id: UUID,
    body: SetTeamPreferenceSchema,
    user_id: CurrentUserId,
    use_case: SetTeamPreferenceUseCaseDep,
) -> TeamPreferenceResult:
    """팀의 경기 조건을 통째로 교체한다. **팀장만.**"""
    return use_case(
        SetTeamPreferenceCommand(
            actor_id=user_id,
            team_id=team_id,
            region_ids=body.region_ids,
            slots=[SlotInput(s.weekday, s.start_time, s.end_time) for s in body.slots],
        )
    )


@match_preference_router.get(
    "/teams/{team_id}/match-preferences", response_model=TeamPreferenceResponse
)
def get_team_preference(
    team_id: UUID, _user_id: CurrentUserId, use_case: GetTeamPreferenceUseCaseDep
) -> TeamPreferenceResult:
    return use_case(GetTeamPreferenceQuery(team_id=team_id))


@match_preference_router.put(
    "/me/match-preferences", response_model=MemberPreferenceResponse
)
def set_member_preference(
    body: SetMemberPreferenceSchema,
    user_id: CurrentUserId,
    use_case: SetMemberPreferenceUseCaseDep,
) -> MemberPreferenceResult:
    """내 경기 조건을 통째로 교체한다. 팀 조건과 절대 안 섞인다."""
    return use_case(
        SetMemberPreferenceCommand(
            user_id=user_id,
            region_ids=body.region_ids,
            slots=[SlotInput(s.weekday, s.start_time, s.end_time) for s in body.slots],
            position_ids=body.position_ids,
        )
    )


@match_preference_router.get(
    "/me/match-preferences", response_model=MemberPreferenceResponse
)
def get_member_preference(
    user_id: CurrentUserId, use_case: GetMemberPreferenceUseCaseDep
) -> MemberPreferenceResult:
    return use_case(GetMemberPreferenceQuery(user_id=user_id))


@match_preference_router.get(
    "/teams/{team_id}/members/match-preferences",
    response_model=list[MemberPreferenceSummaryResponse],
)
def list_member_preferences(
    team_id: UUID,
    user_id: CurrentUserId,
    use_case: ListMemberPreferencesUseCaseDep,
) -> list[MemberPreferenceSummaryResult]:
    """팀원들의 경기 조건. **팀장만 — 남의 팀 조건은 절대 안 보인다.**"""
    return use_case(ListMemberPreferencesQuery(actor_id=user_id, team_id=team_id))


@match_preference_router.get(
    "/teams/{team_id}/match-candidates",
    response_model=list[MatchCandidateResponse],
)
def list_match_candidates(
    team_id: UUID,
    user_id: CurrentUserId,
    use_case: ListMatchCandidatesUseCaseDep,
) -> list[MatchCandidateResult]:
    """"맞는 상대" 후보 목록. 판 크기가 같고 로스터가 찬 팀만, 순서는 서버가
    이미 정렬했다. 🔴 유사도 점수는 없다 — `reasons`가 근거다.
    """
    return use_case(ListMatchCandidatesQuery(actor_id=user_id, team_id=team_id))


@match_preference_router.get(
    "/teams/{team_id}/squad/candidates",
    response_model=list[SquadCandidateResponse],
)
def list_squad_candidates(
    team_id: UUID,
    position_code: str,
    user_id: CurrentUserId,
    use_case: ListSquadCandidatesUseCaseDep,
    grade: str | None = None,
) -> list[SquadCandidateResult]:
    """빈 자리 추천 후보 (미결 `paik` 27번). **부르는 사람이 그 팀 소속이어야 한다.**

    🔴 **「그 팀 소속만」은 부르는 사람 이야기지 후보 이야기가 아니다**
    (2026-09-16에 내가 이 줄을 후보 범위로 잘못 읽고 미결 `min` 20번에
    틀린 근거를 적었다). **후보는 오히려 팀 밖에서 찾는다** —
    `member_match_position`(매칭 선호에 그 포지션을 등록한 사람)에서
    가져오고 현재 팀원·이미 앉은 사람은 뺀다(`squad_recruitment_facts`).

    `grade`를 안 주거나 `"any"`를 주면 등급으로 거르지 않고 팀의 현재 등급
    평균과의 실력 축 거리로 정렬한다. `grade`를 직접 주면(`S`~`F`) **그
    칸으로만 하드 필터**한다. 🔴 리포트 전체·거리 점수는 안 나간다 — 등급 한
    칸(+ `provisional`)만 준다.
    """
    return use_case(
        ListSquadCandidatesQuery(
            actor_id=user_id,
            team_id=team_id,
            position_code=position_code,
            grade=grade,
        )
    )
