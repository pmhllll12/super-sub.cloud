"""사용자·팀 HTTP 경계. 계약 문서 2장.

여기서 하는 일은 **모델 변환과 상태코드**뿐이다. 규칙은 `domain.py`,
흐름은 `service.py`에 있다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.deps import CurrentUserId, get_identity_service
from app.identity.schemas import (
    LoginRequest,
    MeResponse,
    SignupRequest,
    TeamMembership,
    TokenResponse,
    UserResponse,
)
from app.identity.service import IdentityService
from app.identity.stub_repository import STUB_ACCESS_TOKEN, TOKEN_EXPIRES_IN

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(tags=["users"])

_Service = Annotated[IdentityService, Depends(get_identity_service)]


@auth_router.post(
    "/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
def signup(body: SignupRequest, service: _Service) -> UserResponse:
    user = service.signup(body.email, body.password, body.nickname)
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        created_at=user.created_at,
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: _Service) -> TokenResponse:
    service.login(body.email, body.password)
    return TokenResponse(
        access_token=STUB_ACCESS_TOKEN, expires_in=TOKEN_EXPIRES_IN
    )


@users_router.get("/me", response_model=MeResponse)
def read_me(user_id: CurrentUserId, service: _Service) -> MeResponse:
    user, memberships = service.me(user_id)
    return MeResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        created_at=user.created_at,
        teams=[
            TeamMembership(
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
