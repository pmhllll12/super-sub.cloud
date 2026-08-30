"""입력 포트 — 비밀번호 변경."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.me_dto import ChangePasswordCommand


class ChangePasswordUseCase(ABC):
    @abstractmethod
    def __call__(self, command: ChangePasswordCommand) -> None:
        """비밀번호를 바꾸고 **기존 토큰을 전부 무효로** 만든다(SEC-004)."""
