"""team_invitation.position_id — paik 37번

Revision ID: e4a9c6d21b70
Revises: d7b2f1a4c8e5
Create Date: 2026-09-17

초대받은 사람이 **무엇을 해 달라는 초대인지** 알 수 있게 「부르는 자리」를
초대 한 줄에 담는다(`paik` 37번). 지금은 팀 id 하나뿐이라 받는 쪽 화면이
「GK 로 부릅니다」를 그릴 값이 없다.

## nullable 인 이유

부르는 자리를 **안 정하고도 초대할 수 있다** — 「우리 팀에 오세요」가
정상적인 초대다. 필수로 걸면 주장이 자리를 못 정한 상태에서 초대할 길이
막힌다. NULL 은 "안 정했다"이지 "모른다"가 아니다.

## `position_id`(대리키)로 담는 이유

포지션 약칭은 **종목 안에서만 유일**하다(축구 `FW` ≠ 농구 `FW`). 그래서
`squad_member`·`match_position_need` 가 이미 `position_id` 로 담는다 —
같은 판단이다. 클라이언트가 주고받는 것은 여전히 `position_code` 이고
(`GET /positions` 가 id 를 안 내준다) 서버가 팀 종목으로 해석한다.

삭제 규칙을 비워 둔다(기본 RESTRICT) — `squad_member.position_id` 와 같다.
포지션 행은 지우는 것이 아니라 정의를 고치는 자리다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4a9c6d21b70"
down_revision: Union[str, Sequence[str], None] = "d7b2f1a4c8e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "team_invitation", sa.Column("position_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_team_invitation_position",
        "team_invitation",
        "position",
        ["position_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_team_invitation_position", "team_invitation", type_="foreignkey"
    )
    op.drop_column("team_invitation", "position_id")
