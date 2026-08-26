"""라우트 공통 의존성."""

from typing import Annotated

from fastapi import Header

from app.errors import ApiError
from app.stubs import STUB_ACCESS_TOKEN


def require_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """`Authorization: Bearer <token>` 을 검사한다.

    스텁 단계라 로그인이 내준 고정 토큰과 문자열 비교만 한다.
    실제 구현에서는 여기서 JWT 를 검증하고 사용자를 돌려주게 된다.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    if token != STUB_ACCESS_TOKEN:
        raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")
    return token
