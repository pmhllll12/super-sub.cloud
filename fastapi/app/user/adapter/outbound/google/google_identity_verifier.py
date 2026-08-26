"""구글 ID 토큰 검증.

Flutter 의 `google_sign_in` 이 받아 온 **ID 토큰**을 백엔드가 검증하는 방식이다.
서버 리다이렉트 방식(`/auth/google/callback`)은 웹용이라 모바일에 어색하고,
앱이 브라우저를 왕복해야 한다.

검증 항목은 넷이다. **하나라도 빠뜨리면 뚫린다.**

| 항목 | 안 하면 |
|---|---|
| 서명(RS256, 구글 JWKS) | 누구나 아무 토큰이나 만들어 낸다 |
| `aud` = 우리 클라이언트 ID | **다른 앱용 구글 토큰이 그대로 통과한다** |
| `iss` = 구글 | 발급자를 사칭할 수 있다 |
| `exp` | 만료된 토큰이 영원히 산다 |

`aud` 가 특히 중요하다. 구글 토큰이라는 것만 확인하고 대상을 안 보면, **아무
안드로이드 앱이나 구글 로그인을 붙여서 받은 토큰으로 우리 서비스에 로그인할 수 있다.**
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from app.core.errors import ApiError
from app.user.application.ports.output.identity_provider_port import (
    IdentityProviderPort,
)
from app.user.domain.value_objects.external_identity_vo import ExternalIdentity

PROVIDER = "google"

_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
# 구글은 둘 다 발급자로 쓴다. 하나만 허용하면 정상 토큰이 거부된다.
_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleIdentityVerifier(IdentityProviderPort):
    def __init__(
        self,
        audiences: list[str],
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        self._audiences = audiences
        # 테스트에서 가짜 키 공급자를 끼우기 위해 주입 가능하게 둔다.
        # 기본값은 구글 JWKS 를 받아 캐시한다(요청마다 받지 않는다).
        self._jwk_client = jwk_client or PyJWKClient(_JWKS_URL, cache_keys=True)

    def verify(self, id_token: str) -> ExternalIdentity:
        if not self._audiences:
            # 조용히 통과시키지 않는다. 설정이 없으면 검증할 대상이 없다는 뜻이다.
            raise ApiError(
                503,
                "GOOGLE_LOGIN_NOT_CONFIGURED",
                "GOOGLE_CLIENT_IDS 가 설정되지 않았습니다.",
            )

        try:
            key = self._jwk_client.get_signing_key_from_jwt(id_token).key
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self._audiences,
            )
        except (jwt.InvalidTokenError, PyJWKClientError) as exc:
            raise ApiError(
                401, "INVALID_GOOGLE_TOKEN", "구글 토큰이 유효하지 않습니다."
            ) from exc

        # `iss` 는 손으로 본다 — PyJWT 버전에 따라 issuer 인자가 문자열 하나만
        # 받는 경우가 있어서, 구글의 두 발급자를 안전하게 다루려면 이쪽이 확실하다.
        if claims.get("iss") not in _ISSUERS:
            raise ApiError(
                401, "INVALID_GOOGLE_TOKEN", "구글 토큰이 유효하지 않습니다."
            )

        subject = claims.get("sub")
        if not subject:
            raise ApiError(
                401, "INVALID_GOOGLE_TOKEN", "구글 토큰에 sub 가 없습니다."
            )

        return ExternalIdentity(
            provider=PROVIDER,
            subject=str(subject),
            email=str(claims.get("email", "")),
            # 값이 없으면 **확인되지 않은 것으로 본다.** 기본값을 True 로 두면
            # 이메일만 아는 사람이 남의 계정에 연결될 수 있다.
            email_verified=bool(claims.get("email_verified", False)),
            display_name=str(claims.get("name", "")),
        )
