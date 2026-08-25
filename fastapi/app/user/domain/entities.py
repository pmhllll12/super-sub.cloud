"""사용자 컨텍스트의 엔티티. 부록 D 도메인 ① 의 테이블에 대응한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.user.domain.value_objects import Email, Nickname


@dataclass(frozen=True)
class User:
    """`user` 한 행. 자격증명은 여기 없다 — `user_credential` 로 분리했다(부록 D 도메인 ①)."""

    id: UUID
    email: Email
    nickname: Nickname
    created_at: datetime


@dataclass(frozen=True)
class Membership:
    """`team_member` 한 행.

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
