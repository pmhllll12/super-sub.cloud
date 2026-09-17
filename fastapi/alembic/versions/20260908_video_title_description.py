"""video 에 제목과 한 줄 설명을 담는다

Revision ID: 4319b9d12617
Revises: 5d010279c679
Create Date: 2026-09-08

미결 `paik` 5번(3+4 조각의 4). 홈의 영상 모음이 큰 글자로 얹는 값이다. 없으면
이름 없는 칸이 된다.

## 왜 nullable 인가

이미 올라간 클립에는 없다. `player_card.tagline`(미결 `paik` 3번)과 같은 판단 —
빈 문자열 대신 NULL 을 쓰는 것은 "안 정했다"와 "지웠다"를 구별할 필요가 없어서다.
둘 다 화면에서는 "이름 없는 칸"이 맞다.

## 길이

제목 100, 설명 280. 설명은 목록 카드 한 줄에 들어가는 값이라 길면 잘린다 —
화면이 감당 못 하는 길이를 받아 두고 나중에 자르면 쓴 것과 보이는 것이 달라진다
(`tagline` 20자 결정과 같은 이유, 값만 크다).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4319b9d12617"
down_revision: Union[str, Sequence[str], None] = "5d010279c679"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "video", sa.Column("title", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "video", sa.Column("description", sa.String(length=280), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("video", "description")
    op.drop_column("video", "title")
