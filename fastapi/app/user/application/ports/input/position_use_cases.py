"""포지션 조회 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.position_dto import (
    ListPositionsQuery,
    PositionResult,
)


class ListPositionsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListPositionsQuery) -> list[PositionResult]:
        """종목별 포지션 목록. 없는 종목으로 거르면 `422 UNKNOWN_SPORT`."""
