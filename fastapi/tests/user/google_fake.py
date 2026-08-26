"""구글 ID 토큰을 **네트워크 없이** 흉내 낸다.

로컬에서 RSA 키를 만들어 우리가 직접 서명하고, 검증기에는 그 공개키를 주는
가짜 JWKS 클라이언트를 끼운다. 그래서 서명·`aud`·`iss`·`exp` 검사를 실제로
통과·실패시켜 볼 수 있다.

**구글에 붙지 않고도 검증 로직 전부를 시험할 수 있다는 것이 요점이다.**
"""

from __future__ import annotations

import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CLIENT_ID = "test-client-id.apps.googleusercontent.com"
ISSUER = "https://accounts.google.com"

# 모듈당 한 번만 만든다. 2048비트 생성이 테스트마다 돌면 느려진다.
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
PUBLIC_KEY = _KEY.public_key()


class _FakeSigningKey:
    def __init__(self, key) -> None:
        self.key = key


class FakeJwkClient:
    """`PyJWKClient` 자리에 끼운다. 늘 같은 공개키를 준다."""

    def __init__(self, key=PUBLIC_KEY) -> None:
        self._signing_key = _FakeSigningKey(key)

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return self._signing_key


def make_id_token(
    *,
    subject: str = "1234567890",
    email: str = "google-user@super-sub.example",
    email_verified: bool = True,
    name: str = "구글사용자",
    audience: str = CLIENT_ID,
    issuer: str = ISSUER,
    expires_in: int = 600,
) -> str:
    now = int(time.time())
    claims = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "email": email,
        "email_verified": email_verified,
        "name": name,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(claims, _PRIVATE_PEM, algorithm="RS256")


# 서명 검증을 시험하려면 **같은 알고리즘에 다른 키**여야 한다. HS256 으로 서명하면
# 알고리즘 불일치로 걸려서, 정작 서명 검증이 도는지는 확인되지 않는다.
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PEM = _OTHER_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


def make_token_signed_by_other_key(**kw) -> str:
    """구글이 아닌 다른 키로 서명한 토큰. 클레임은 전부 정상이다."""
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": kw.get("audience", CLIENT_ID),
        "sub": "impostor",
        "email": "impostor@super-sub.example",
        "email_verified": True,
        "iat": now,
        "exp": now + 600,
    }
    return jwt.encode(claims, _OTHER_PEM, algorithm="RS256")
