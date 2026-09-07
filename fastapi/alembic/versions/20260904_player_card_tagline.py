"""player_card 에 사람이 정하는 한 줄을 담는다

Revision ID: c9e15a3b7d24
Revises: b7c41e2f9a08
Create Date: 2026-09-04

미결 `paik` 3번. 카드에 보이는 별명(`THREE LUNGS`)이 **화면의 붙박이 상수**라
모든 카드가 글자까지 똑같았다. 계약에 필드가 없어 서버에서 받아올 데가 없었다.

## 왜 `nickname` 이 아닌가

`user.nickname` 은 이미 있고 **사람의 이름**이다. 카드에 크게 박히는 이 한 줄은
스스로 붙이는 별명이라 다른 값이다. `title`(호칭)도 이미 있는데 그쪽은 **분석이
주는 것**이라 사람이 못 고른다. 셋이 서로 다른 개념이라 이름을 나눈다.

## 왜 nullable 인가

이미 만들어진 카드가 있고, 안 정한 사람도 카드는 있어야 한다. 빈 문자열 대신
NULL 을 쓰는 것은 **"안 정했다"와 "지웠다"를 구별할 필요가 없기 때문**이다 —
둘 다 화면에서는 안 보이는 것이 맞다.

🔴 **부록 D 의 `player_card` 에는 이 컬럼이 없다.** ERD 갱신은 미결 항목으로
올렸다(`sort_order` 와 같은 처리).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e15a3b7d24"
down_revision: Union[str, Sequence[str], None] = "b7c41e2f9a08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 20자. 카드에 한 줄로 크게 들어가는 값이라 길면 잘리거나 글자가 작아진다 —
    # 화면이 감당할 수 없는 길이를 받아 두고 나중에 자르면 사람이 쓴 것과
    # 보이는 것이 달라진다.
    op.add_column(
        "player_card", sa.Column("tagline", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("player_card", "tagline")
