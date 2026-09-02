"""팀 라우터. 계약 문서 3-3절.

**여기는 도메인을 모른다.** Command/Query DTO 로 바꿔 넘기고, 돌아온 Result DTO 를
`response_model` 이 응답 스키마로 변환한다.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.team_schema import (
    AddMemberSchema,
    CreateTeamSchema,
    TeamResponse,
)
from app.user.application.dtos.team_dto import (
    CreateTeamCommand,
    JoinTeamCommand,
    LeaveTeamCommand,
    TeamQuery,
    TeamResult,
)
from app.user.dependencies.team_providers import (
    CreateTeamUseCaseDep,
    JoinTeamUseCaseDep,
    LeaveTeamUseCaseDep,
    ReadTeamUseCaseDep,
)

team_router = APIRouter(tags=["teams"])


@team_router.post(
    "/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED
)
def create_team(
    body: CreateTeamSchema, user_id: CurrentUserId, use_case: CreateTeamUseCaseDep
) -> TeamResult:
    """팀을 만든다. **만든 사람이 주장(`owner`)으로 함께 들어간다.**"""
    return use_case(
        CreateTeamCommand(
            actor_id=user_id,
            name=body.name,
            region=body.region,
            sport_code=body.sport_code,
        )
    )


@team_router.get("/teams/{team_id}", response_model=TeamResponse)
def read_team(
    team_id: UUID, user_id: CurrentUserId, use_case: ReadTeamUseCaseDep
) -> TeamResult:
    """팀과 현재 구성원. 소속이 아니어도 볼 수 있다(가입하려면 먼저 봐야 한다)."""
    return use_case(TeamQuery(actor_id=user_id, team_id=team_id))


@team_router.post(
    "/teams/{team_id}/members",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_team_member(
    team_id: UUID,
    body: AddMemberSchema,
    user_id: CurrentUserId,
    use_case: JoinTeamUseCaseDep,
) -> TeamResult:
    """가입하거나(본문 없이) 주장이 남을 넣는다(`user_id` 를 담아서)."""
    return use_case(
        JoinTeamCommand(actor_id=user_id, team_id=team_id, user_id=body.user_id)
    )


@team_router.delete(
    "/teams/{team_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_team_member(
    team_id: UUID,
    member_id: UUID,
    user_id: CurrentUserId,
    use_case: LeaveTeamUseCaseDep,
) -> None:
    """탈퇴(본인)하거나 방출한다(주장). **행은 지우지 않고 `left_at` 을 채운다.**"""
    use_case(
        LeaveTeamCommand(actor_id=user_id, team_id=team_id, user_id=member_id)
    )
