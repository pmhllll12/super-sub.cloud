"""입력 포트 — 내 정보 수정."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.me_dto import MeResult, UpdateMeCommand


class UpdateMeUseCase(ABC):
    @abstractmethod
    def __call__(self, command: UpdateMeCommand) -> MeResult:
        """닉네임을 바꾸고 **바뀐 뒤의 내 정보 전체**를 돌려준다."""
