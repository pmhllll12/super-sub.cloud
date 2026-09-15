"""지역 목록 출력 포트. `paik` 19번."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.domain.entities.region_entity import RegionEntity


class RegionPort(ABC):
    @abstractmethod
    def list_regions(self) -> list[RegionEntity]:
        """전체 지역 목록. `city`·`district` 순."""
