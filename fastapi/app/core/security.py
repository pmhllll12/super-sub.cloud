"""액세스 토큰 발급과 검증.

**어느 컨텍스트에도 속하지 않는다.** 인증은 `user` 가 발급하고 모든 컨텍스트가
검증하므로, 여기 두면 `card` 가 `user` 를 임포트하지 않아도 된다.

HS256(대칭키)을 쓴다. 발급과 검증을 같은 프로세스가 하므로 비대칭키가 필요 없다.
**나중에 검증만 하는 서비스가 따로 생기면** 그때 RS256 으로 바꾼다 — 그 서비스에
서명 키를 주지 않기 위해서다.

🔴 **`JWT_SECRET` 이 없으면 토큰을 발급하지 않는다.** 예전에는 서명 없는 문자열
(`stub-token-for-<uuid>`)을 돌려줬는데, 그건 누구나 남의 id 를 적어 넣으면 그
사람으로 인증되는 상태였다. 조용한 대체값 대신 **크게 실패한다.**
"""

from __future__ import annotations

import time
from uuid import UUID

import jwt

from app.core.config import settings
from app.core.errors import ApiError

_ALGORITHM = "HS256"

# 계약 문서 0장 — 리프레시 없이 액세스 토큰 하나로 간다.
TOKEN_EXPIRES_IN = 7 * 24 * 60 * 60  # 7일


def _secret() -> str:
    if not settings.jwt_secret:
        raise ApiError(
            503,
            "AUTH_NOT_CONFIGURED",
            "JWT_SECRET 이 설정되지 않아 토큰을 발급할 수 없습니다.",
        )
    return settings.jwt_secret


def issue_access_token(user_id: UUID) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + TOKEN_EXPIRES_IN,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def verify_access_token(authorization: str | None) -> UUID:
    """`Authorization: Bearer <token>` 을 검사하고 사용자 id 를 돌려준다.

    401 을 두 가지로 나눈다. **클라이언트 동작이 다르기 때문이다** — 헤더가 없으면
    로그인 화면으로, 토큰이 무효하면 토큰을 버리고 재로그인으로 보낸다.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
        return UUID(payload["sub"])
    except ApiError:
        raise
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        # 만료·서명 불일치·형식 오류를 구분하지 않는다. 클라이언트가 할 일은
        # 어느 쪽이든 "토큰을 버리고 다시 로그인" 하나뿐이다.
        raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.") from exc
