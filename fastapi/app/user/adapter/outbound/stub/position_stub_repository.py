"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다.

🔴 이 목록은 마이그레이션 `20260902_match_tables` 가 넣는 값과 같아야 한다.
갈리면 스텁으로는 통과하고 실물에서 깨진다 — `test_position_db.py` 가 대조한다.
"""

from __future__ import annotations

from app.user.application.ports.output.position_port import PositionPort
from app.user.domain.entities.position_entity import PositionEntity

_POSITIONS: list[PositionEntity] = [
    PositionEntity("football", "GK", "골키퍼"),
    PositionEntity("football", "DF", "수비수"),
    PositionEntity("football", "MF", "미드필더"),
    PositionEntity("football", "FW", "공격수"),
    PositionEntity("baseball", "P", "투수"),
    PositionEntity("baseball", "C", "포수"),
    PositionEntity("baseball", "IF", "내야수"),
    PositionEntity("baseball", "OF", "외야수"),
    PositionEntity("basketball", "G", "가드"),
    PositionEntity("basketball", "F", "포워드"),
    PositionEntity("basketball", "C", "센터"),
]

_SPORTS = {"football", "baseball", "basketball"}


class StubPositionRepository(PositionPort):
    def sport_exists(self, sport_code: str) -> bool:
        return sport_code in _SPORTS

    def list_positions(self, sport_code: str | None) -> list[PositionEntity]:
        rows = [
            p
            for p in _POSITIONS
            if sport_code is None or p.sport_code == sport_code
        ]
        return sorted(rows, key=lambda p: (p.sport_code, p.code))
