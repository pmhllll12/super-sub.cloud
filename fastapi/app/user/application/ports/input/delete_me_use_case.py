"""입력 포트 — 탈퇴."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.me_dto import DeleteMeCommand


class DeleteMeUseCase(ABC):
    @abstractmethod
    def __call__(self, command: DeleteMeCommand) -> None:
        """계정과 파생 데이터를 지운다(SEC-006)."""
