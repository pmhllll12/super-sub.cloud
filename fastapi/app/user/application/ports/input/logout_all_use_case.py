"""입력 포트 — 모든 기기에서 로그아웃."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class LogoutAllUseCase(ABC):
    @abstractmethod
    def __call__(self, user_id: UUID) -> None:
        """그 사용자에게 발급된 **모든 토큰을 무효로** 만든다(SEC-004)."""
