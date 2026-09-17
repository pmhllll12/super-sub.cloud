"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다.

🔴 이 목록은 마이그레이션 `20260902_match_tables` 가 넣는 값과 같아야 한다.
갈리면 스텁으로는 통과하고 실물에서 깨진다 — `test_position_db.py` 가 대조한다.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from app.user.application.ports.output.position_port import PositionPort
from app.user.domain.entities.position_entity import PositionEntity

_NAMES: list[tuple[str, str, str]] = [
    ("football", "GK", "골키퍼"),
    ("football", "DF", "수비수"),
    ("football", "MF", "미드필더"),
    ("football", "FW", "공격수"),
    ("baseball", "P", "투수"),
    ("baseball", "C", "포수"),
    ("baseball", "IF", "내야수"),
    ("baseball", "OF", "외야수"),
    ("basketball", "G", "가드"),
    ("basketball", "F", "포워드"),
    ("basketball", "C", "센터"),
]


def _fake_id(sport_code: str, code: str) -> UUID:
    """스텁 전용 id — `(종목, 약칭)` 에서 **늘 같은 값**이 나온다.

    🔴 **실물 DB 의 id 가 아니다.** 여기서 만든 값을 실서버에 보내면
    `422 UNKNOWN_POSITION` 이다. 매번 `uuid4()` 로 흔들면 계약 테스트가
    한 요청에서 받은 id 를 다음 요청에 쓸 수 없어 고정값으로 둔다.
    """
    return uuid5(NAMESPACE_URL, f"supersub:stub:position:{sport_code}:{code}")


_POSITIONS: list[PositionEntity] = [
    PositionEntity(_fake_id(sport, code), sport, code, label)
    for sport, code, label in _NAMES
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
