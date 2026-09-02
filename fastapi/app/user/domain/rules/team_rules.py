"""팀 권한 규칙. **HTTP도 DB도 없다** — 순수 함수라 아무것도 안 띄우고 테스트한다.

권한을 인터랙터 안에 `if` 로 흩어 놓으면 **어디까지가 규칙인지 읽어서 알 수 없다.**
여기 모아 두면 규칙만 따로 검사할 수 있다.
"""

from __future__ import annotations

from uuid import UUID

from app.user.domain.entities.team_entity import TeamMemberEntity
from app.user.domain.value_objects.team_role_vo import TeamRole


def can_add_member(actor_role: TeamRole | None, adding_self: bool) -> bool:
    """멤버를 넣을 수 있는가.

    - **자기 자신**은 아무나 넣을 수 있다 (가입). 이때 `actor_role` 은 None 이다
    - **남**을 넣는 것은 `owner` 만 할 수 있다
    """
    if adding_self:
        return True
    return actor_role is TeamRole.OWNER


def can_remove_member(
    actor_id: UUID, target_id: UUID, actor_role: TeamRole | None
) -> bool:
    """멤버를 뺄 수 있는가. 본인(탈퇴)이거나 `owner`(방출)여야 한다."""
    if actor_id == target_id:
        return True
    return actor_role is TeamRole.OWNER


def is_last_owner(members: list[TeamMemberEntity], user_id: UUID) -> bool:
    """이 사람이 나가면 팀에 `owner` 가 없어지는가.

    없어지면 **아무도 남을 추가할 수 없는 팀**이 된다. 소유권 이양 API 가 없는
    지금은 되돌릴 방법이 없으므로 미리 막는다.
    """
    owners = [m for m in members if m.role is TeamRole.OWNER]
    return len(owners) == 1 and owners[0].user_id == user_id
