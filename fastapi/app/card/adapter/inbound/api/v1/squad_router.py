"""스쿼드 라우터. 계약 문서 3-7절.

경로가 `/teams/{team_id}/squad` **단수**인 것은 팀당 하나로 다루기 때문이다
(스키마는 여러 개를 허용한다 — `squad_orm.py` 참조).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.card.adapter.inbound.api.schemas.squad_schema import (
    EnlistCardSchema,
    SquadResponse,
)
from app.card.application.dtos.squad_dto import (
    CreateSquadCommand,
    DischargeMemberCommand,
    EnlistCardCommand,
    PublicSquadQuery,
    SquadResult,
    TeamSquadQuery,
)
from app.card.dependencies.squad_providers import (
    CreateSquadUseCaseDep,
    DischargeMemberUseCaseDep,
    EnlistCardUseCaseDep,
    PublicSquadUseCaseDep,
    TeamSquadUseCaseDep,
)
from app.core.deps import CurrentUserId

squad_router = APIRouter(tags=["squads"])


@squad_router.post(
    "/teams/{team_id}/squad",
    response_model=SquadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "이미 스쿼드가 있었다. 있는 것을 그대로 돌려준다"}},
)
def create_squad(
    team_id: UUID,
    user_id: CurrentUserId,
    use_case: CreateSquadUseCaseDep,
    response: Response,
) -> SquadResult:
    """스쿼드를 만든다. **주장만 할 수 있고, 멱등이다.**

    두 번 불러도 스쿼드는 하나고 슬러그도 그대로다 — 두 번째부터는 200 이 온다.
    클라이언트가 재시도해도 공유 링크가 바뀌면 안 되기 때문이다.
    """
    creation = use_case(CreateSquadCommand(actor_id=user_id, team_id=team_id))
    if not creation.created:
        response.status_code = status.HTTP_200_OK
    return creation.squad


@squad_router.get("/teams/{team_id}/squad", response_model=SquadResponse)
def read_team_squad(
    team_id: UUID, user_id: CurrentUserId, use_case: TeamSquadUseCaseDep
) -> SquadResult:
    """팀 화면에서 보는 스쿼드. **소속이면 볼 수 있다.**

    슬러그를 아는 사람은 누구나 볼 수 있으므로 이 검사는 비밀을 지키는 것이
    아니라 **팀 id 로 남의 팀 구성을 훑는 것**을 막는다.
    """
    return use_case(TeamSquadQuery(actor_id=user_id, team_id=team_id))


@squad_router.post(
    "/teams/{team_id}/squad/members",
    response_model=SquadResponse,
    status_code=status.HTTP_201_CREATED,
)
def enlist_card(
    team_id: UUID,
    body: EnlistCardSchema,
    user_id: CurrentUserId,
    use_case: EnlistCardUseCaseDep,
) -> SquadResult:
    """카드를 등재한다. **주장만 할 수 있고, 팀 구성원의 카드만 된다.**

    바뀐 스쿼드 전체를 돌려준다 — 화면이 목록을 다시 그리기 때문이다.
    """
    return use_case(
        EnlistCardCommand(
            actor_id=user_id,
            team_id=team_id,
            player_card_id=body.player_card_id,
            position_code=body.position_code,
        )
    )


@squad_router.delete(
    "/teams/{team_id}/squad/members/{member_id}", response_model=SquadResponse
)
def discharge_member(
    team_id: UUID,
    member_id: UUID,
    user_id: CurrentUserId,
    use_case: DischargeMemberUseCaseDep,
) -> SquadResult:
    """등재를 뺀다. **카드는 지워지지 않는다** — 스쿼드에서 빠질 뿐이다."""
    return use_case(
        DischargeMemberCommand(
            actor_id=user_id, team_id=team_id, member_id=member_id
        )
    )


@squad_router.get("/squads/{public_slug}", response_model=SquadResponse)
def read_public_squad(
    public_slug: str, use_case: PublicSquadUseCaseDep
) -> SquadResult:
    """공유용이라 인증하지 않는다 — 공개 카드(`/cards/{slug}`)와 같은 결이다."""
    return use_case(PublicSquadQuery(public_slug=public_slug))
