"""사용자 컨텍스트의 HTTP 경계. 계약 문서 2장.

여기서 하는 일은 **모델 변환과 상태코드**뿐이다. 규칙은 `domain/`,
흐름은 `application/` 에 있다.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.deps import CurrentUserId
from app.user.adapter.inbound.schemas import (
    LoginRequest,
    MeResponse,
    SignupRequest,
    TeamMembershipResponse,
    TokenResponse,
    UserResponse,
)
from app.user.dependencies import Login, Me, Signup
from app.user.domain.entities import User

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(tags=["users"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=str(user.email),
        nickname=str(user.nickname),
        created_at=user.created_at,
    )


@auth_router.post(
    "/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
def signup(body: SignupRequest, use_case: Signup) -> UserResponse:
    return _user_response(use_case(body.email, body.password, body.nickname))


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, use_case: Login) -> TokenResponse:
    issued = use_case(body.email, body.password)
    return TokenResponse(
        access_token=issued.access_token, expires_in=issued.expires_in
    )


@users_router.get("/me", response_model=MeResponse)
def read_me(user_id: CurrentUserId, use_case: Me) -> MeResponse:
    user, memberships = use_case(user_id)
    base = _user_response(user)
    return MeResponse(
        **base.model_dump(),
        teams=[
            TeamMembershipResponse(
                team_id=m.team_id,
                name=m.name,
                region=m.region,
                sport_code=m.sport_code,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in memberships
        ],
    )
