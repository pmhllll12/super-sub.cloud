"""analysis_metric_criterion.title_earned — ho 40번

Revision ID: 5e91b4a7c3d8
Revises: 3f8a1c6d2b90
Create Date: 2026-09-16

부록 D 도메인 ②. `paik` 23번(「받은 호칭」의 기준)에 답하며 봉투에 추가된
`result.breakdown[].title_earned`(schema_version 1.2)를 적재한다.

## 왜 필요한가

`title`은 **모든 등급에 있다** — 0등급도 「무너지는 축」같은 문구를 받는다.
「받은 호칭」인지는 `title`의 유무가 아니라 이 필드(최고 등급 + 루브릭이 그
문구를 실제로 적었을 것)로만 가른다. 안 넣으면 화면이 `report.json`을 따로
읽거나, 없는 사이에 0등급에 호칭을 다시 달게 된다.

## nullable이다

`skipped` 행과 이 필드가 생기기 전(schema_version 1.1) 적재분은 NULL —
`False`로 채우면 "호칭이 없다"와 "판단 자체가 없었다"가 섞인다(`ho` 21번과
같은 판단).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5e91b4a7c3d8"
down_revision: Union[str, Sequence[str], None] = "3f8a1c6d2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_metric_criterion",
        sa.Column("title_earned", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_metric_criterion", "title_earned")
