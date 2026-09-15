"""메모리 지역 목록. 계약 테스트가 DB 없이 돌기 위한 것이다. `paik` 19번.

🔴 실물은 `www/src/lib/regions.ts`의 60개를 그대로 시드한다(마이그레이션
`20260915_match_preferences`). 스텁은 그 부분집합이다 — 테스트가 지역 계층
(같은 구/같은 시/그 외)을 검증할 수 있게 서울 2곳·경기 1곳처럼 **같은 시
안에 구가 둘인 경우**를 반드시 포함한다.

`match` 컨텍스트 스텁(팀·개인 경기 조건)이 이 목록의 id를 그대로 참조한다 —
`REGIONS_BY_LABEL`을 가져다 쓴다.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.user.application.ports.output.region_port import RegionPort
from app.user.domain.entities.region_entity import RegionEntity

_REGIONS: list[RegionEntity] = [
    RegionEntity(uuid4(), "서울", "강남구", "서울 강남구"),
    RegionEntity(uuid4(), "서울", "서초구", "서울 서초구"),
    RegionEntity(uuid4(), "서울", "마포구", "서울 마포구"),
    RegionEntity(uuid4(), "경기", "수원시", "경기 수원시"),
    RegionEntity(uuid4(), "경기", "성남시", "경기 성남시"),
    RegionEntity(uuid4(), "부산", "해운대구", "부산 해운대구"),
]

REGIONS_BY_LABEL: dict[str, RegionEntity] = {r.label: r for r in _REGIONS}
REGIONS_BY_ID: dict[UUID, RegionEntity] = {r.id: r for r in _REGIONS}


class StubRegionRepository(RegionPort):
    def list_regions(self) -> list[RegionEntity]:
        return sorted(_REGIONS, key=lambda r: (r.city, r.district))
