"""`match_application`. 부록 D 도메인 ④."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ApplicationEntity:
    """경기 1건에 대한 한 사람의 지원 1건.

    **상태값이 없다.** 두 시각으로 상태를 읽는다(부록 D.5 — 매칭 확정은 사람이 한다).
    `nickname` 은 표시용이라 `user` 에서 읽어 온다(저장되는 것은 `user_id` 뿐이다).
    """

    id: UUID
    match_id: UUID
    user_id: UUID
    nickname: str
    team_accepted_at: datetime | None
    user_accepted_at: datetime | None

    @property
    def is_confirmed(self) -> bool:
        """둘 다 수락해야 확정이다. 한쪽만으로는 성사가 아니다."""
        return self.team_accepted_at is not None and self.user_accepted_at is not None

    @property
    def started_by_team(self) -> bool:
        """팀이 먼저 제안한 건인가. 사람이 지원한 건이면 False 다."""
        return self.team_accepted_at is not None and self.user_accepted_at is None
