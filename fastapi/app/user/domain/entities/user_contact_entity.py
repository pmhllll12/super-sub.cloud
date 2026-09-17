"""`user_contact`. 부록 D 도메인 ①. 미결 `jin` 35번.

**일방적 신청이 아니라 상호 관계다.** 신청은 한쪽이 하지만(그래서
`requester_user_id`/`target_user_id`로 방향이 있다), 수락되면 **양쪽 다** 서로를
지인 목록에서 본다 — `match_application`이 "시작한 쪽"과 "수락하는 쪽"을 나누는
것과 같은 모양이지만, 여기는 둘 다 수락해야 하는 게 아니라 **대상만** 수락하면
끝난다는 점이 다르다(팀의 제안·사람의 지원처럼 "누가 시작했든 상대만 수락하면
확정"인 자리다).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class UserContactEntity:
    """지인 신청(대기중) 또는 지인 관계(수락됨) 1건.

    `accepted_at`이 `None`이면 대기중이다 — 상태 컬럼 대신 시각으로 상태를 읽는
    것은 `match_application`과 같은 판단이다(부록 D.5).
    """

    id: UUID
    requester_user_id: UUID
    target_user_id: UUID
    note: str | None
    accepted_at: datetime | None
    created_at: datetime

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None


@dataclass(frozen=True)
class UserContactSummary:
    """지인 목록 한 줄. 상대방이 **평평하게** 실린다(`ApplicationResult.nickname`과
    같은 판단 — 표시용으로 조인해 온 값은 평평하게 둔다).

    `note`는 내가 신청자일 때만 채워진다 — 상대 시점에서는 늘 `None`이다.
    """

    contact_id: UUID
    user_id: UUID
    nickname: str
    note: str | None
    accepted_at: datetime
    # 그 사람의 공개 카드 슬러그 — 카드를 안 만들었으면 `None`(미결 `paik` 39번).
    # 🔴 내부 id 를 밖으로 내보내지 않으려고 **서버가 여기서 바꿔** 준다.
    card_public_slug: str | None = None
