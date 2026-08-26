"""소속 관련 규칙. **HTTP도 DB도 없다** — 순수 함수라 아무것도 안 띄우고 테스트한다."""

from __future__ import annotations

from app.user.domain.entities.membership_entity import MembershipEntity


def active_memberships(memberships: list[MembershipEntity]) -> list[MembershipEntity]:
    """지금 소속된 팀만 남긴다.

    `team_member` 는 탈퇴해도 행이 남는다 — `left_at` 으로 소프트 삭제한다.
    **거르지 않으면 나간 팀이 내 정보에 그대로 나온다.**
    """
    return [m for m in memberships if m.is_active]
