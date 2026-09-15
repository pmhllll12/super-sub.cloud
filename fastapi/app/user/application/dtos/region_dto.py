"""지역 목록 조회 DTO. `paik` 19번."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListRegionsQuery:
    pass


@dataclass(frozen=True)
class RegionResult:
    id: UUID
    city: str
    district: str
    label: str
