"""입력 포트 — 공개 카드."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.card.application.dtos.card_dto import PublicCardQuery, PublicCardResult


class PublicCardUseCase(ABC):
    @abstractmethod
    def __call__(self, query: PublicCardQuery) -> PublicCardResult:
        """슬러그로 보는 공개 카드 (SFR-009). 없으면 404 로 떨어진다."""
