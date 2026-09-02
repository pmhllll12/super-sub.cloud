"""경기 라우터. 계약 문서 3-4절."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId
from app.match.adapter.inbound.api.schemas.match_schema import (
    CreateMatchSchema,
    MatchResponse,
)
from app.match.application.dtos.match_dto import (
    CreateMatchCommand,
    MatchQuery,
    MatchResult,
    PositionNeedInput,
)
from app.match.dependencies.match_providers import (
    CreateMatchUseCaseDep,
    ReadMatchUseCaseDep,
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


@match_router.get("/matches/{match_id}", response_model=MatchResponse)
def read_match(
    match_id: UUID, user_id: CurrentUserId, use_case: ReadMatchUseCaseDep
) -> MatchResult:
    """경기 1건과 필요 포지션. 인증만 하면 누구나 본다 — 모집 글이다."""
    return use_case(MatchQuery(match_id=match_id))
