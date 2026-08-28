"""가입·로그인 라우터. 계약 문서 2장.

**여기는 도메인을 모른다.** HTTP 스키마 → Command DTO 로 바꿔 유스케이스에 넘기고,
돌아온 Result DTO 를 `response_model` 이 응답 스키마로 변환한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUserId
from app.core.rate_limit import limit_auth_requests
from app.user.adapter.inbound.api.schemas.auth_schema import (
    GoogleLoginSchema,
    LoginSchema,
    SignupResponse,
    SignupSchema,
    TokenResponse,
)
from app.user.application.dtos.login_dto import (
    GoogleLoginCommand,
    LoginCommand,
    LoginResult,
)
from app.user.application.dtos.signup_dto import SignupCommand, SignupResult
from app.user.dependencies.google_login_provider import GoogleLoginUseCaseDep
from app.user.dependencies.login_provider import LoginUseCaseDep
from app.user.dependencies.logout_all_provider import LogoutAllUseCaseDep
from app.user.dependencies.signup_provider import SignupUseCaseDep

# 라우터에 달아 둔다 — **여기 추가되는 엔드포인트가 자동으로 제한을 받는다**(SEC-009).
auth_router = APIRouter(
    prefix="/auth", tags=["auth"], dependencies=[Depends(limit_auth_requests)]
)


@auth_router.post(
    "/signup", status_code=status.HTTP_201_CREATED, response_model=SignupResponse
)
def signup(body: SignupSchema, use_case: SignupUseCaseDep) -> SignupResult:
    return use_case(
        SignupCommand(
            email=body.email, password=body.password, nickname=body.nickname
        )
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginSchema, use_case: LoginUseCaseDep) -> LoginResult:
    return use_case(LoginCommand(email=body.email, password=body.password))


@auth_router.post("/google", response_model=TokenResponse)
def google_login(
    body: GoogleLoginSchema, use_case: GoogleLoginUseCaseDep
) -> LoginResult:
    """구글 ID 토큰으로 로그인한다. 처음이면 계정이 만들어진다.

    응답은 비밀번호 로그인과 **같다** — 클라이언트는 이후 흐름을 하나로 유지한다.
    """
    return use_case(GoogleLoginCommand(id_token=body.id_token))


@auth_router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user_id: CurrentUserId, use_case: LogoutAllUseCaseDep) -> None:
    """이 계정에 발급된 **모든 토큰을 무효로** 만든다(SEC-004).

    지금 쓰고 있는 토큰도 함께 끊긴다 — 다시 로그인해야 한다. 기기를 잃어버렸을 때
    쓰라고 만든 것이므로 "지금 것만 남기기"는 두지 않는다.
    """
    use_case(user_id)
