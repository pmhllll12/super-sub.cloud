"""입력 포트 — 구글 로그인."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.login_dto import GoogleLoginCommand, LoginResult


class GoogleLoginUseCase(ABC):
    @abstractmethod
    def __call__(self, command: GoogleLoginCommand) -> LoginResult:
        """구글 ID 토큰으로 로그인시킨다. 처음이면 계정을 만든다."""
