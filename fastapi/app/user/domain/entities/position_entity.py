"""`position` 참조 데이터 한 줄. 부록 D 도메인 ①.

종목별 포지션이다. **저장은 다른 도메인(`squad_member`·`match_position_need`)이
하고, 여기는 그 목록을 읽어 내보내는 자리**다 — 그래서 도메인 규칙이 없다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionEntity:
    sport_code: str
    code: str
    label: str
