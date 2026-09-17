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
    CreateTeamInvitationSchema,
    CreateTeamSchema,
    MyTeamInvitationResponse,
    SetMemberRoleSchema,
    TeamInvitationResponse,
    TeamResponse,
    UpdateTeamSchema,
)
from app.user.application.dtos.team_dto import (
    CancelTeamInvitationCommand,
    CreateTeamCommand,
    CreateTeamInvitationCommand,
    DisbandTeamCommand,
    JoinTeamCommand,
    LeaveTeamCommand,
    MyTeamInvitationResult,
    MyTeamInvitationsQuery,
    RespondTeamInvitationCommand,
    SetMemberRoleCommand,
    TeamInvitationResult,
    TeamInvitationsQuery,
    TeamQuery,
    TeamResult,
    UpdateTeamCommand,
)
from app.user.dependencies.team_providers import (
    AcceptTeamInvitationUseCaseDep,
    CancelTeamInvitationUseCaseDep,
    CreateTeamInvitationUseCaseDep,
    CreateTeamUseCaseDep,
    DisbandTeamUseCaseDep,
    JoinTeamUseCaseDep,
    LeaveTeamUseCaseDep,
    ListMyTeamInvitationsUseCaseDep,
    ListTeamInvitationsUseCaseDep,
    ReadTeamUseCaseDep,
    SetMemberRoleUseCaseDep,
    RejectTeamInvitationUseCaseDep,
    UpdateTeamUseCaseDep,
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


@team_router.patch("/teams/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: UUID,
    body: UpdateTeamSchema,
    user_id: CurrentUserId,
    use_case: UpdateTeamUseCaseDep,
) -> TeamResult:
    """팀 이름·지역을 고친다. **주장만.**

    지금까지 팀은 만들 때 적은 값이 영영 고정이었다 — 지역은 경기 탐색
    (`GET /matches?region=`)이 거르는 값이라 틀리면 그 팀이 검색에서 안 걸린다.

    | | |
    |---|---|
    | 403 `FORBIDDEN` | 주장이 아니다 |
    | 404 `TEAM_NOT_FOUND` | 없는 팀이다 |
    | 422 `VALIDATION_ERROR` | 빈 값·길이 초과·`null`(지우기는 안 된다) |

    🔴 `sport_code` 는 못 바꾼다 — 본문에 자리가 없다(`UpdateTeamSchema` 참고).
    """
    return use_case(
        UpdateTeamCommand(
            actor_id=user_id,
            team_id=team_id,
            name=body.name,
            region=body.region,
        )
    )


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


@team_router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def disband_team(
    team_id: UUID, user_id: CurrentUserId, use_case: DisbandTeamUseCaseDep
) -> None:
    """팀을 해체한다. **주장만.** (`paik` 35번)

    그전에는 혼자 만든 팀을 **영영 못 버렸다** — 마지막 주장은 `LAST_OWNER`
    로 나갈 수 없는데 팀을 없앨 길도 없었다.

    🔴 **행을 지우지 않는다.** `disbanded_at` 을 찍고 남은 구성원을 전부
    내보내고(그래서 `GET /me` 의 `teams` 에서 사라진다) 대기 중이던 초대·경기
    신청을 `cancelled` 로 닫는다. 지난 경기·평가는 그대로 남는다 — 그것들이
    이 팀 이름을 가리키기 때문이다(`team_member.left_at` 과 같은 판단).

    해체된 팀은 **새로 만드는 자리만** 막힌다(가입·초대·팀 수정 → 409
    `TEAM_DISBANDED`). 읽기는 그대로 된다.

    | | |
    |---|---|
    | 403 `FORBIDDEN` | 주장이 아니다 |
    | 404 `TEAM_NOT_FOUND` | 없는 팀이다 |
    | 409 `TEAM_DISBANDED` | 이미 해체된 팀이다 |
    | 409 `TEAM_HAS_UPCOMING_MATCH` | 앞으로 있을 경기가 있다 — 상대에게는 약속이라 먼저 정리해야 한다 |
    """
    use_case(DisbandTeamCommand(actor_id=user_id, team_id=team_id))


@team_router.patch(
    "/teams/{team_id}/members/{member_id}", response_model=TeamResponse
)
def set_team_member_role(
    team_id: UUID,
    member_id: UUID,
    body: SetMemberRoleSchema,
    user_id: CurrentUserId,
    use_case: SetMemberRoleUseCaseDep,
) -> TeamResult:
    """구성원의 역할을 바꾼다 — 실질적으로 **주장 세우기**. **주장만.** (`paik` 35번)

    `LAST_OWNER` 가 "다른 주장을 먼저 세워야 합니다"라고 안내하는데 그전에는
    **세울 경로가 없었다.** 이것이 그 실물이다.

    🔴 **기존 주장은 그대로 주장이다** — 넘기고 나가려면 세운 다음
    `DELETE /teams/{team_id}/members/{내 id}` 로 나가면 된다.

    | | |
    |---|---|
    | 403 `FORBIDDEN` | 주장이 아니다 |
    | 404 `TEAM_NOT_FOUND` · `NOT_A_MEMBER` | 없는 팀이다 · 그 사람이 이 팀 구성원이 아니다 |
    | 409 `TEAM_DISBANDED` | 해체된 팀이다 |
    """
    return use_case(
        SetMemberRoleCommand(
            actor_id=user_id,
            team_id=team_id,
            user_id=member_id,
            role=body.role,
        )
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


# ---------------------------------------------------------------------------
# 팀 초대 (`team_invitation`). `min` 20번.
#
# 동의 없이 `POST /teams/{id}/members`로 바로 넣지 않는다(2026-09-10 박민호
# 결정) — 초대를 보내고 **받은 사람 본인이 수락해야** 소속이 된다.
# ---------------------------------------------------------------------------


@team_router.post(
    "/teams/{team_id}/invitations",
    response_model=TeamInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team_invitation(
    team_id: UUID,
    body: CreateTeamInvitationSchema,
    user_id: CurrentUserId,
    use_case: CreateTeamInvitationUseCaseDep,
) -> TeamInvitationResult:
    """우리 팀(`team_id`)이 개인을 초대한다. **주장만.**

    받은 사람에게 알림(`team_invitation_sent`)이 간다.

    | | |
    |---|---|
    | 403 `FORBIDDEN` | 주장이 아니다 |
    | 404 `USER_NOT_FOUND` | 그 사람이 없다 |
    | 409 `ALREADY_MEMBER` | 이미 이 팀의 구성원이다 |
    | 409 `ALREADY_INVITED` | 이미 그 사람에게 보낸 대기 중 초대가 있다 |
    | 422 `UNKNOWN_POSITION` | 이 팀 종목에 없는 `position_code` 다 |

    `position_code`(「부르는 자리」)는 **선택이다** — 안 주면 자리를 안 정한
    초대가 된다(`paik` 37번).
    """
    return use_case(
        CreateTeamInvitationCommand(
            actor_id=user_id,
            team_id=team_id,
            invited_user_id=body.invited_user_id,
            position_code=body.position_code,
        )
    )


@team_router.get(
    "/teams/{team_id}/invitations",
    response_model=list[TeamInvitationResponse],
)
def list_team_invitations(
    team_id: UUID,
    user_id: CurrentUserId,
    use_case: ListTeamInvitationsUseCaseDep,
) -> list[TeamInvitationResult]:
    """그 팀이 보낸 초대 전부(상태 무관), 최신순. **주장만** 본다."""
    return use_case(TeamInvitationsQuery(actor_id=user_id, team_id=team_id))


@team_router.get("/me/invitations", response_model=list[MyTeamInvitationResponse])
def list_my_invitations(
    user_id: CurrentUserId, use_case: ListMyTeamInvitationsUseCaseDep
) -> list[MyTeamInvitationResult]:
    """내가 받은, 아직 답 안 한 초대 목록.

    🔴 **초대 한 줄만 보고 정할 수 있게** 팀 이름·지역·종목과 그 팀 스쿼드의
    공개 슬러그를 함께 싣는다(`paik` 37번). 받는 사람은 아직 그 팀 소속이
    아니라 팀 화면을 거치지 않는다.

    `squad_public_slug` 는 `GET /squads/{slug}`(누구나 읽는다)에 그대로 넣어
    그 팀 판을 그리는 데 쓴다 — 어느 자리가 비었는지 보고 정하라는 것이다.

    🔴 **경기 시각·구장은 없다** — 초대는 경기에 묶이지 않는다.
    """
    return use_case(MyTeamInvitationsQuery(user_id=user_id))


@team_router.post(
    "/me/invitations/{invitation_id}/accept",
    response_model=TeamInvitationResponse,
)
def accept_team_invitation(
    invitation_id: UUID,
    user_id: CurrentUserId,
    use_case: AcceptTeamInvitationUseCaseDep,
) -> TeamInvitationResult:
    """받은 사람 본인이 수락한다. **그 팀의 구성원이 된다.**

    | | |
    |---|---|
    | 404 `TEAM_INVITATION_NOT_FOUND` | 초대가 없다 |
    | 403 `FORBIDDEN` | 내가 받은 사람이 아니다 |
    | 409 `TEAM_INVITATION_ALREADY_RESPONDED` | 이미 답이 났다 |
    """
    return use_case(
        RespondTeamInvitationCommand(actor_id=user_id, invitation_id=invitation_id)
    )


@team_router.post(
    "/me/invitations/{invitation_id}/reject",
    response_model=TeamInvitationResponse,
)
def reject_team_invitation(
    invitation_id: UUID,
    user_id: CurrentUserId,
    use_case: RejectTeamInvitationUseCaseDep,
) -> TeamInvitationResult:
    """받은 사람 본인이 거절한다. 팀 주장(들)에게 알림이 간다."""
    return use_case(
        RespondTeamInvitationCommand(actor_id=user_id, invitation_id=invitation_id)
    )


@team_router.delete(
    "/teams/{team_id}/invitations/{invitation_id}",
    response_model=TeamInvitationResponse,
)
def cancel_team_invitation(
    team_id: UUID,
    invitation_id: UUID,
    user_id: CurrentUserId,
    use_case: CancelTeamInvitationUseCaseDep,
) -> TeamInvitationResult:
    """보낸 팀(`team_id`) 주장이 스스로 무른다. **아직 `pending`일 때만.**

    🔴 `204`가 아니라 무른 초대를 그대로 돌려준다 — `team_match_request`의
    취소와 같은 이유(삭제라기보다 상태 전이라서, 클라이언트가 같은 파서를
    쓸 수 있다).
    """
    return use_case(
        CancelTeamInvitationCommand(
            actor_id=user_id, team_id=team_id, invitation_id=invitation_id
        )
    )
