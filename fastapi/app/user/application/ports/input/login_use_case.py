"""입력 포트 — 로그인."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.login_dto import LoginCommand, LoginResult


class LoginUseCase(ABC):
    @abstractmethod
    def __call__(self, command: LoginCommand) -> LoginResult:
        """토큰을 발급한다. 자격증명이 틀리면 401 로 떨어진다."""
