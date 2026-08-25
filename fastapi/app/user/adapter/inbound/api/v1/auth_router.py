"""가입·로그인 라우터. 계약 문서 2장.

**여기는 도메인을 모른다.** HTTP 스키마 → Command DTO 로 바꿔 유스케이스에 넘기고,
돌아온 Result DTO 를 `response_model` 이 응답 스키마로 변환한다.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.user.adapter.inbound.api.schemas.auth_schema import (
    LoginSchema,
    SignupResponse,
    SignupSchema,
    TokenResponse,
)
from app.user.application.dtos.login_dto import LoginCommand, LoginResult
from app.user.application.dtos.signup_dto import SignupCommand, SignupResult
from app.user.dependencies.login_provider import LoginUseCaseDep
from app.user.dependencies.signup_provider import SignupUseCaseDep

auth_router = APIRouter(prefix="/auth", tags=["auth"])


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
