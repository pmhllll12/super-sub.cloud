"""스쿼드 홈 판의 배치를 서버에 담는다 — formation · 격자 칸

Revision ID: 6a0f3d23662c
Revises: 9d4e88f5b6c2
Create Date: 2026-09-09

미결 `paik` 9번. 홈 스쿼드 판이 판 크기를 고르고 카드를 칸으로 옮길 수 있게
됐는데(사용자 요청), `squad_member` 가 아는 것은 `position_id` 하나뿐이라
셋(판 크기 · 칸 · 손으로 정한 포지션) 중 둘을 담을 데가 없었다. 지금은 그
브라우저의 `localStorage` 에 있어 다른 기기에서는 처음 판으로 열린다.

## 무엇을 넣나 (미결 `paik` 9번 「안 A」)

| 컬럼 | 왜 |
|---|---|
| `squad.formation` `varchar(8)` NULL | 판 크기(`"3:3"`·`"5:5"`·`"7:7"`). 판당 하나라 `squad` 에 둔다 |
| `squad_member.grid_col` `smallint` NULL | 카드가 선 **열** 번호. 🔴 픽셀 아님 |
| `squad_member.grid_row` `smallint` NULL | 카드가 선 **행** 번호. 행이 포지션 라인이다(계약 3-7) |

## 왜 전부 nullable

- 옛 행: 이 셋이 생기기 전에 만든 스쿼드·등재.
- 등재만 하고 판에 안 올린 카드: `grid_col`·`grid_row` 가 NULL 이다. 🔴 **둘 중
  하나만 찬 상태는 없다** — 앱(스키마·인터랙터)이 both-or-neither 로 막는다.
  DB CHECK 를 걸지 않는 것은 `analysis_job.status` 를 제약으로 안 거는 것과 같은
  판단이다(값 규칙이 늘 때 마이그레이션 없이).

## 🔴 격자 크기는 계약이 정한다

지금 격자는 3열 × 4행이고 행이 포지션 라인이다(0 FW · 1 MF · 2 DF · 3 GK).
그 값을 바꾸면 저장된 `grid_col`·`grid_row` 의 뜻도 바뀌므로 **그때 리매핑
마이그레이션이 필요하다.** 정본은 `docs/api-contract.md` 3-7 절.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a0f3d23662c'
down_revision: Union[str, Sequence[str], None] = '9d4e88f5b6c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "squad", sa.Column("formation", sa.String(length=8), nullable=True)
    )
    op.add_column(
        "squad_member", sa.Column("grid_col", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "squad_member", sa.Column("grid_row", sa.SmallInteger(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("squad_member", "grid_row")
    op.drop_column("squad_member", "grid_col")
    op.drop_column("squad", "formation")
