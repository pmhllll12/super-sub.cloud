"""지역 목록 입력 포트. `paik` 19번."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.region_dto import ListRegionsQuery, RegionResult


class ListRegionsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListRegionsQuery) -> list[RegionResult]:
        """전체 지역 목록."""
