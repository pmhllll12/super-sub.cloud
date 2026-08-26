"""로그인 유스케이스가 주고받는 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass(frozen=True)
class GoogleLoginCommand:
    """인바운드 → 유스케이스.

    결과는 비밀번호 로그인과 **같은 `LoginResult`** 다. 클라이언트 입장에서
    "토큰을 받는다"는 결과가 같아야 화면 흐름이 하나로 유지된다.
    """

    id_token: str
