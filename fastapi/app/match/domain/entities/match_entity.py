"""`match` 와 필요 포지션. 부록 D 도메인 ④."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PositionNeedEntity:
    """경기 1건의 포지션 1종 필요분.

    `code`·`label` 은 `position` 에서 읽어 온 표시용이다 — 저장되는 것은
    `position_id` 뿐이다(약칭은 종목 안에서만 유일해서 코드로는 못 가리킨다).
    """

    position_id: UUID
    code: str
    label: str
    head_count: int


@dataclass(frozen=True)
class MatchEntity:
    """등록된 경기 1건.

    🔴 **종목이 없다.** `match -> team -> sport_code` 로 결정된다(부록 D.4).
    여기에 종목을 들이면 팀 종목과 어긋날 수 있는 두 번째 진실이 생긴다.
    """

    id: UUID
    team_id: UUID
    played_at: datetime
    place: str
    needs: list[PositionNeedEntity] = field(default_factory=list)
