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
