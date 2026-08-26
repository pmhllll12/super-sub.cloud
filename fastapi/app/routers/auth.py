"""인증 — 가입과 로그인. 계약 문서 2장."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, status

from app import stubs
from app.errors import ApiError
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def signup(body: SignupRequest) -> UserResponse:
    """가입.

    스텁이라 저장하지 않는다. 중복 경로를 눌러볼 수 있도록 데모 계정 이메일만
    409 로 막는다.
    """
    if body.email == stubs.DEMO_EMAIL:
        raise ApiError(
            409, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다."
        )

    return UserResponse(
        id=uuid4(),
        email=body.email,
        nickname=body.nickname,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """로그인.

    이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다 — 구분하면
    가입 여부가 새어 나간다(계약 문서 2장).
    """
    if body.email != stubs.DEMO_EMAIL or body.password != stubs.DEMO_PASSWORD:
        raise ApiError(
            401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다."
        )

    return TokenResponse(
        access_token=stubs.STUB_ACCESS_TOKEN,
        expires_in=stubs.TOKEN_EXPIRES_IN,
    )
