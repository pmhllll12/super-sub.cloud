"""경기 라우터. 계약 문서 3-4절."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUserId
from app.match.adapter.inbound.api.schemas.match_schema import (
    ApplicationResponse,
    ApplySchema,
    CreateMatchSchema,
    MatchResponse,
    MatchSearchResponse,
)
from app.match.application.dtos.match_dto import (
    AcceptApplicationCommand,
    ApplicationResult,
    ApplicationsQuery,
    ApplyCommand,
    CreateMatchCommand,
    MatchQuery,
    MatchResult,
    MatchSearchQuery,
    MatchSearchResult,
    TeamMatchesQuery,
    PositionNeedInput,
)
from app.match.dependencies.match_providers import (
    AcceptApplicationUseCaseDep,
    ApplyToMatchUseCaseDep,
    CreateMatchUseCaseDep,
    ListApplicationsUseCaseDep,
    ListTeamMatchesUseCaseDep,
    ReadMatchUseCaseDep,
    SearchMatchesUseCaseDep,
)

match_router = APIRouter(tags=["matches"])


@match_router.post(
    "/teams/{team_id}/matches",
    response_model=MatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_match(
    team_id: UUID,
    body: CreateMatchSchema,
    user_id: CurrentUserId,
    use_case: CreateMatchUseCaseDep,
) -> MatchResult:
    """경기를 등록한다. **주장만 할 수 있다** — 팀을 대표하는 약속이라서다."""
    return use_case(
        CreateMatchCommand(
            actor_id=user_id,
            team_id=team_id,
            played_at=body.played_at,
            place=body.place,
            needs=[
                PositionNeedInput(
                    position_code=n.position_code, head_count=n.head_count
                )
                for n in body.needs
            ],
        )
    )


@match_router.get(
    "/teams/{team_id}/matches", response_model=list[MatchResponse]
)
def list_team_matches(
    team_id: UUID, user_id: CurrentUserId, use_case: ListTeamMatchesUseCaseDep
) -> list[MatchResult]:
    """그 팀의 **다가오는** 경기. 이른 것이 앞에 온다.

    지난 경기는 담기지 않는다 — 목록은 모집 글이다. 지난 경기도
    `GET /matches/{id}` 로는 여전히 읽힌다.
    """
    return use_case(TeamMatchesQuery(team_id=team_id))


@match_router.get("/matches", response_model=MatchSearchResponse)
def search_matches(
    user_id: CurrentUserId,
    use_case: SearchMatchesUseCaseDep,
    sport_code: str | None = None,
    region: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> MatchSearchResult:
    """종목·지역으로 **다가오는** 경기를 찾는다 (SFR-010 의 반대편).

    🔴 **팀 id 를 몰라도 되는 유일한 경로다.** 다른 목록(`/teams/{id}/matches`)은
    그 팀을 이미 알아야 하므로, 용병이 지원할 경기를 찾을 수단이 없었다.

    `region` 은 부분 일치이고 대소문자를 가리지 않는다. 종목 코드가 실재하지
    않으면 빈 배열이 아니라 422 다 — 오타와 "경기가 없다"를 가르기 위해서다.
    """
    return use_case(
        MatchSearchQuery(
            sport_code=sport_code, region=region, page=page, size=size
        )
    )


@match_router.get("/matches/{match_id}", response_model=MatchResponse)
def read_match(
    match_id: UUID, user_id: CurrentUserId, use_case: ReadMatchUseCaseDep
) -> MatchResult:
    """경기 1건과 필요 포지션. 인증만 하면 누구나 본다 — 모집 글이다."""
    return use_case(MatchQuery(match_id=match_id))
@match_router.post(
    "/matches/{match_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_match(
    match_id: UUID,
    body: ApplySchema,
    user_id: CurrentUserId,
    use_case: ApplyToMatchUseCaseDep,
) -> ApplicationResult:
    """지원하거나(본문 없이) 주장이 제안한다(`user_id` 를 담아서).

    시작한 쪽 시각만 차고 **반대쪽이 수락해야 확정**이다.
    """
    return use_case(
        ApplyCommand(actor_id=user_id, match_id=match_id, user_id=body.user_id)
    )


@match_router.post(
    "/matches/{match_id}/applications/{application_id}/accept",
    response_model=ApplicationResponse,
)
def accept_application(
    match_id: UUID,
    application_id: UUID,
    user_id: CurrentUserId,
    use_case: AcceptApplicationUseCaseDep,
) -> ApplicationResult:
    """반대쪽이 수락한다. 둘 다 차면 `confirmed` 가 참이 된다."""
    return use_case(
        AcceptApplicationCommand(
            actor_id=user_id, match_id=match_id, application_id=application_id
        )
    )


@match_router.get(
    "/matches/{match_id}/applications",
    response_model=list[ApplicationResponse],
)
def list_applications(
    match_id: UUID, user_id: CurrentUserId, use_case: ListApplicationsUseCaseDep
) -> list[ApplicationResult]:
    """주장은 전부, 그 외에는 **자기 건만** 본다 — 지원자 명단은 팀의 정보다."""
    return use_case(ApplicationsQuery(actor_id=user_id, match_id=match_id))
