"""지역 목록 조회 인터랙터. `paik` 19번."""

from __future__ import annotations

from app.user.application.dtos.region_dto import ListRegionsQuery, RegionResult
from app.user.application.ports.input.region_use_cases import ListRegionsUseCase
from app.user.application.ports.output.region_port import RegionPort


class ListRegionsInteractor(ListRegionsUseCase):
    def __init__(self, repository: RegionPort) -> None:
        self._repository = repository

    def __call__(self, query: ListRegionsQuery) -> list[RegionResult]:
        return [
            RegionResult(id=r.id, city=r.city, district=r.district, label=r.label)
            for r in self._repository.list_regions()
        ]
