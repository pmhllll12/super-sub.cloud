"""`position` 참조 데이터 한 줄. 부록 D 도메인 ①.

종목별 포지션이다. **저장은 다른 도메인(`squad_member`·`match_position_need`)이
하고, 여기는 그 목록을 읽어 내보내는 자리**다 — 그래서 도메인 규칙이 없다.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PositionEntity:
    """🔴 **`id` 를 함께 내보낸다.** 약칭(`code`)은 종목 안에서만 유일해서
    그것만으로는 한 줄을 못 가리킨다 — 다른 도메인이 포지션을 지목할 때
    (`member_match_position.position_id` 등) 쓰는 값은 이 대리키다.
    """

    id: UUID
    sport_code: str
    code: str
    label: str
