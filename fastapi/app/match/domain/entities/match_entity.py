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


@dataclass(frozen=True)
class MatchListingEntity:
    """탐색 목록의 한 줄. 경기 하나에 **주최 팀의 표시용 값**을 얹은 것이다.

    용병이 경기를 고르는 기준이 종목·지역·팀이라, 목록에는 그 셋이 함께 있어야
    한다. 경기 id 만 주면 화면이 팀을 한 건씩 다시 물어야 한다.

    🔴 **`MatchEntity` 에 종목을 넣지 않는 원칙은 그대로다.** 이것은 저장되는
    모양이 아니라 **조회 결과**다 — 값은 매번 `team` 에서 읽어 오므로 팀 종목과
    어긋날 수가 없다. 포지션의 `code`·`label` 을 표시용으로 들고 다니는 것과
    같은 자리다.
    """

    match: MatchEntity
    team_name: str
    region: str
    sport_code: str
