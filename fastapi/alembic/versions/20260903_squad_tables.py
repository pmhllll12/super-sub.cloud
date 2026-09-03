"""squad tables

Revision ID: d52e8f1a6b34
Revises: c41d7a6b8e02
Create Date: 2026-09-03

부록 D 도메인 ③ 의 남은 둘이다. `player_card` 는 08-26 에 들어갔는데 팀 단위로
묶는 자리가 없어 `/teams/{id}` 의 스쿼드 탭이 비어 있었다.

## `team_id` 에 유일 제약을 걸지 않았다

부록 D.7 이 이 테이블에 정한 유일 제약은 `public_slug` 하나뿐이다. **ERD 에 없는
제약은 늘리지 않는다** — 늘리면 스키마가 문서보다 좁아지고, 나중에 문서를 따르려는
사람이 왜 막히는지 알 수 없게 된다.

다만 `squad` 에는 이름 컬럼이 없어 한 팀에 여러 개를 만들면 서로 구별할 수가
없다. 그래서 **애플리케이션이 팀당 하나로 다룬다**(생성이 멱등이다). 이름 컬럼이
생기면 스키마 변경 없이 여러 개를 열 수 있다.

## 삭제 규칙 — 하나만 걸고 둘은 비웠다

| 외래키 | 규칙 | 왜 |
|---|---|---|
| `squad_member.squad_id` | CASCADE | 등재는 스쿼드 안에서만 뜻이 있다. 스쿼드가 사라지면 함께 사라져야 한다 |
| `squad.team_id` | 기본(RESTRICT) | 부록 D.6 이 **팀 해체 시의 처리를 정하지 않았다** |
| `squad_member.player_card_id` | 기본(RESTRICT) | 탈퇴한 사람의 등재를 지울지 익명으로 남길지가 안 정해졌다 |

정해지지 않은 것을 여기서 임의로 정하면 나중에 스키마와 문서가 어긋난다 —
`user_title` 에서와 같은 판단이다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd52e8f1a6b34'
down_revision: Union[str, Sequence[str], None] = 'c41d7a6b8e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "squad",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("public_slug", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_slug", name="uq_squad_public_slug"),
    )
    op.create_table(
        "squad_member",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("squad_id", sa.Uuid(), nullable=False),
        sa.Column("player_card_id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["squad_id"], ["squad.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_card.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["position.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("squad_id", "player_card_id", name="uq_squad_member"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("squad_member")
    op.drop_table("squad")
