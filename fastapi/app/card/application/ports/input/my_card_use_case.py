"""입력 포트 — 내 카드."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.card.application.dtos.card_dto import MyCardQuery, MyCardResult


class MyCardUseCase(ABC):
    @abstractmethod
    def __call__(self, query: MyCardQuery) -> MyCardResult:
        """내 카드. 없으면 404 로 떨어진다."""
