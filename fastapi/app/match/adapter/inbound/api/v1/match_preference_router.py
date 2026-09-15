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
    TeamPreferenceResponse,
)
from app.match.application.dtos.match_preference_dto import (
    GetMemberPreferenceQuery,
    GetTeamPreferenceQuery,
    ListMatchCandidatesQuery,
    ListMemberPreferencesQuery,
    MatchCandidateResult,
    MemberPreferenceResult,
    MemberPreferenceSummaryResult,
    SetMemberPreferenceCommand,
    SetTeamPreferenceCommand,
    SlotInput,
    TeamPreferenceResult,
)
from app.match.dependencies.match_preference_providers import (
    GetMemberPreferenceUseCaseDep,
    GetTeamPreferenceUseCaseDep,
    ListMatchCandidatesUseCaseDep,
    ListMemberPreferencesUseCaseDep,
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
