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


def can_edit_team(actor_role: TeamRole | None) -> bool:
    """팀 자체(이름·지역)를 고칠 수 있는가. **`owner` 만.**

    `can_add_member` 와 달리 「본인」 예외가 없다 — 팀 정보는 소속 전체에게
    보이는 값이라 아무나 고치면 남의 팀 이름이 바뀐다.
    """
    return actor_role is TeamRole.OWNER


def can_remove_member(
    actor_id: UUID, target_id: UUID, actor_role: TeamRole | None
) -> bool:
    """멤버를 뺄 수 있는가. 본인(탈퇴)이거나 `owner`(방출)여야 한다."""
    if actor_id == target_id:
        return True
    return actor_role is TeamRole.OWNER


def can_disband_team(actor_role: TeamRole | None) -> bool:
    """팀을 해체할 수 있는가. **`owner` 만** (`paik` 35번).

    `can_edit_team` 과 같은 이유로 「본인」 예외가 없다 — 구성원 아무나
    해체하면 남의 팀이 사라진다.
    """
    return actor_role is TeamRole.OWNER


def can_set_member_role(actor_role: TeamRole | None) -> bool:
    """남의 역할을 바꿀 수 있는가. **`owner` 만** (`paik` 35번).

    이것이 `is_last_owner` 가 가리키던 「다른 주장을 먼저 세운다」의 실물이다.
    그전에는 그 안내가 **가리키는 경로가 없어 실행 불가능**했다.
    """
    return actor_role is TeamRole.OWNER


def is_last_owner(members: list[TeamMemberEntity], user_id: UUID) -> bool:
    """이 사람이 나가면 팀에 `owner` 가 없어지는가.

    없어지면 **아무도 남을 추가할 수 없는 팀**이 된다. 되돌리는 길은 둘이다
    (`paik` 35번, 2026-09-17): 다른 사람을 주장으로 세우거나
    (`PATCH /teams/{id}/members/{user_id}`), 팀을 해체하거나
    (`DELETE /teams/{id}`). 혼자인 팀은 세울 상대가 없으므로 후자다.
    """
    owners = [m for m in members if m.role is TeamRole.OWNER]
    return len(owners) == 1 and owners[0].user_id == user_id
