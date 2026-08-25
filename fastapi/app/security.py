"""액세스 토큰 발급과 검증.

**어느 컨텍스트에도 속하지 않는다.** 인증은 `user`가 발급하고 모든 컨텍스트가
검증하므로, 여기 두면 `card`가 `user`를 임포트하지 않아도 된다.

지금은 스텁이라 서명하지 않는다. 다만 **토큰이 사용자 id 를 실어 나르는 형태**는
JWT 와 같게 맞춰 두었다 — 나중에 진짜 JWT 로 바꿀 때 이 파일만 고치면 되고
호출하는 쪽은 그대로다.
"""

from __future__ import annotations

from uuid import UUID

from app.errors import ApiError

# 계약 문서 0장 — 리프레시 없이 액세스 토큰 하나로 간다.
TOKEN_EXPIRES_IN = 7 * 24 * 60 * 60  # 7일

_STUB_PREFIX = "stub-token-for-"


def issue_access_token(user_id: UUID) -> str:
    """스텁 토큰. 진짜 JWT 로 바뀔 때 서명·만료가 여기 들어간다."""
    return f"{_STUB_PREFIX}{user_id}"


def verify_access_token(authorization: str | None) -> UUID:
    """`Authorization: Bearer <token>` 을 검사하고 사용자 id 를 돌려준다.

    401 을 두 가지로 나눈다. **클라이언트 동작이 다르기 때문이다** —
    헤더가 없으면 로그인 화면으로, 토큰이 무효하면 토큰을 버리고 재로그인으로 보낸다.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith(_STUB_PREFIX):
        raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

    try:
        return UUID(token.removeprefix(_STUB_PREFIX))
    except ValueError as exc:
        raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.") from exc
