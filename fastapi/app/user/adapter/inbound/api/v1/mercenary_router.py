"""용병 매칭 라우터 — 내 프로필 관리 + 후보 검색.

RAG의 "R"만 여기 있다. 대화(생성)는 `www/`의 챗봇이 이 검색 결과를 자연어로
엮는다 — 이 계약은 데이터 형태까지만 정한다(pending `min` 7번·16번).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.mercenary_schema import (
    AvailableSlotSchema,
    CandidateResponse,
    MercenaryProfileResponse,
    PositionRefSchema,
    SearchCandidatesSchema,
    UpdateMercenaryProfileSchema,
)
from app.user.application.dtos.mercenary_dto import (
    AvailableSlotDto,
    CandidateResult,
    GetMercenaryProfileQuery,
    MercenaryProfileResult,
    PositionRefDto,
    SearchCandidatesQuery,
    UpdateMercenaryProfileCommand,
)
from app.user.dependencies.get_mercenary_profile_provider import (
    GetMercenaryProfileUseCaseDep,
)
from app.user.dependencies.search_candidates_provider import (
    SearchCandidatesUseCaseDep,
)
from app.user.dependencies.update_mercenary_profile_provider import (
    UpdateMercenaryProfileUseCaseDep,
)

mercenary_router = APIRouter(tags=["mercenary-matching"])


def _to_position_dtos(
    schemas: list[PositionRefSchema] | None,
) -> list[PositionRefDto] | None:
    if schemas is None:
        return None
    return [PositionRefDto(sport_code=s.sport_code, code=s.code) for s in schemas]


def _to_slot_dtos(
    schemas: list[AvailableSlotSchema] | None,
) -> list[AvailableSlotDto] | None:
    if schemas is None:
        return None
    return [AvailableSlotDto(day=s.day, start=s.start, end=s.end) for s in schemas]


def _to_response(result: MercenaryProfileResult) -> MercenaryProfileResponse:
    return MercenaryProfileResponse(
        user_id=result.user_id,
        preferred_positions=[
            PositionRefSchema(sport_code=p.sport_code, code=p.code)
            for p in result.preferred_positions
        ],
        available_slots=[
            AvailableSlotSchema(day=s.day, start=s.start, end=s.end)
            for s in result.available_slots
        ],
        location=result.location,
        skill_summary=result.skill_summary,
        is_searchable=result.is_searchable,
    )


@mercenary_router.get("/me/mercenary-profile", response_model=MercenaryProfileResponse)
def read_mercenary_profile(
    user_id: CurrentUserId, use_case: GetMercenaryProfileUseCaseDep
) -> MercenaryProfileResponse:
    result = use_case(GetMercenaryProfileQuery(user_id=user_id))
    return _to_response(result)


@mercenary_router.patch("/me/mercenary-profile", response_model=MercenaryProfileResponse)
def update_mercenary_profile(
    body: UpdateMercenaryProfileSchema,
    user_id: CurrentUserId,
    use_case: UpdateMercenaryProfileUseCaseDep,
) -> MercenaryProfileResponse:
    """`is_searchable=true`가 되려면(요청에서 켜거나 이미 켜져 있으면) 포지션·
    가능 시간·소개가 전부 채워져 있어야 한다 — 아니면 `422
    MERCENARY_PROFILE_INCOMPLETE`.
    """
    command = UpdateMercenaryProfileCommand(
        user_id=user_id,
        preferred_positions=_to_position_dtos(body.preferred_positions),
        available_slots=_to_slot_dtos(body.available_slots),
        location=body.location,
        skill_summary=body.skill_summary,
        is_searchable=body.is_searchable,
    )
    result = use_case(command)
    return _to_response(result)


@mercenary_router.post(
    "/matching/search-candidates", response_model=list[CandidateResponse]
)
def search_candidates(
    body: SearchCandidatesSchema,
    _user_id: CurrentUserId,
    use_case: SearchCandidatesUseCaseDep,
) -> list[CandidateResult]:
    """`query_text`를 서버가 임베딩으로 바꿔 코사인 유사도로 검색한다.

    클라이언트는 벡터를 직접 만들어 보내지 않는다 — 임의 벡터를 받으면
    검색 랭킹을 조작할 수 있다. 로그인만 하면 누구나 부를 수 있다(팀 주장
    한정 여부는 아직 안 정했다 — pending `min` 16번).
    """
    return use_case(
        SearchCandidatesQuery(
            sport_code=body.sport_code,
            position_code=body.position_code,
            query_text=body.query_text,
            limit=body.limit,
        )
    )
