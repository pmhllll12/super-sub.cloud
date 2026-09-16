"""팀 초대(`team_invitation`) 규칙. **HTTP도 DB도 없다.** `min` 20번.

`team_match_request`(팀 대 팀, `match` 컨텍스트)와 상태 전이 모양만 같다 —
이건 팀이 **개인**을 데려오는 것이라 대상 쪽 권한 판단이 다르다(팀 역할이
아니라 그 사람 본인인가).
"""

from __future__ import annotations

from uuid import UUID

from app.user.domain.value_objects.team_role_vo import TeamRole

PENDING = "pending"
ACCEPTED = "accepted"
REJECTED = "rejected"
CANCELLED = "cancelled"


def can_manage(team_role: TeamRole | None) -> bool:
    """이 초대를 보내거나 무를 수 있는가. **그 팀 주장만.**"""
    return team_role is TeamRole.OWNER


def can_respond(invited_user_id: UUID, actor_id: UUID) -> bool:
    """수락·거절할 수 있는가. **받은 사람 본인만** — 대신 답할 수 없다."""
    return actor_id == invited_user_id


def is_respondable(status: str) -> bool:
    """아직 답이 안 난 초대인가 — 수락·거절·취소는 `pending`일 때만 뜻이 있다."""
    return status == PENDING
