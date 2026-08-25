"""입력 포트 — 내 정보."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.me_dto import MeQuery, MeResult


class MeUseCase(ABC):
    @abstractmethod
    def __call__(self, query: MeQuery) -> MeResult:
        """내 정보와 **지금 소속된** 팀을 돌려준다."""
