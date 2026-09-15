"""`region` 참조 데이터 한 줄. 부록 D 도메인 ①. `paik` 19번.

`match` 컨텍스트의 팀·개인 경기 조건이 참조한다 — 여기는 목록을 읽어 내보내는
자리라 도메인 규칙이 없다(`position_entity.py`와 같은 판단).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RegionEntity:
    id: UUID
    city: str
    district: str
    label: str
