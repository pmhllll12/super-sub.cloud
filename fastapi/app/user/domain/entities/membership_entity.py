"""`team_member` (+ `team` 표시 정보) 에 대응하는 엔티티. 부록 D 도메인 ①."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class MembershipEntity:
    """한 사람의 한 팀 소속 구간 1건.

    `left_at` 이 채워져 있으면 나간 소속이다. 탈퇴해도 행이 남는 이유는
    경기·평가 이력이 이 행을 참조하기 때문이다(부록 D 도메인 ①).
    """

    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: datetime
    left_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.left_at is None
