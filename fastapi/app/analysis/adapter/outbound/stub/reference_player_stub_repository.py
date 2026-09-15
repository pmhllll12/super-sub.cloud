"""메모리 선수 목록. 계약 테스트가 DB 없이 돌기 위한 것이다. `paik` 29번.

실물 두 명(`rovelli`·`castanheira`, `www/src/components/analysis/
AnalysisStage.tsx`의 `COMPARE`)을 그대로 시드한다. `report_key`는 테스트가
`FakeStorage`(`video_stub_repository.py`)의 `put_blob`으로 미리 채워 둘
자리다 — 이 파일은 키 이름만 안다.
"""

from __future__ import annotations

from app.analysis.application.ports.output.reference_player_port import (
    ReferencePlayerPort,
)
from app.analysis.domain.entities.reference_player_entity import (
    ReferencePlayerEntity,
)

_PLAYERS: list[ReferencePlayerEntity] = [
    ReferencePlayerEntity(
        id="rovelli",
        name="에스테반 로벨리",
        report_key="reports/pro/pexels-15436954/report.json",
    ),
    ReferencePlayerEntity(
        id="castanheira",
        name="티아구 카스탄헤이라",
        report_key="reports/pro/pexels-15436958/report.json",
    ),
]

PLAYERS_BY_ID: dict[str, ReferencePlayerEntity] = {p.id: p for p in _PLAYERS}


class StubReferencePlayerRepository(ReferencePlayerPort):
    def list_players(self) -> list[ReferencePlayerEntity]:
        return sorted(_PLAYERS, key=lambda p: p.name)

    def find_player(self, player_id: str) -> ReferencePlayerEntity | None:
        return PLAYERS_BY_ID.get(player_id)
