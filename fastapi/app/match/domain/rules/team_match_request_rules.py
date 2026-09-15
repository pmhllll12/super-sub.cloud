"""팀 대 팀 경기 신청(`team_match_request`) 규칙. **HTTP도 DB도 없다.** `paik` 17번.

개인의 `match_application`과 달리 신청·수락 둘 다 **그 팀 주장만** 할 수 있다.
"""

from __future__ import annotations

PENDING = "pending"
ACCEPTED = "accepted"
REJECTED = "rejected"
CANCELLED = "cancelled"


def can_manage(team_role: str | None) -> bool:
    """이 신청에 대해(생성·수락·거절·취소) 행동할 수 있는가. **주장만.**"""
    from app.match.domain.rules.match_rules import OWNER_ROLE

    return team_role == OWNER_ROLE


def is_respondable(status: str) -> bool:
    """아직 답이 안 난 신청인가 — 수락·거절·취소는 `pending`일 때만 뜻이 있다."""
    return status == PENDING
