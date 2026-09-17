"""video 에 원본 파일 이름을 담는다

Revision ID: 2598dc30f0cb
Revises: 98f9cbdc74f4
Create Date: 2026-09-08

미결 `jin` 24번. 저장 키는 콘솔에서 알아볼 수 있게 슬러그로 짓지만(한글·영숫자만
남기고 잘림) 손실적이다. 사람이 "문제 영상"을 되짚고 에이전트가 제대로 돌았는지
확인하려면 원래 이름이 온전히 필요해서 컬럼으로 따로 둔다.

`player_card.tagline`(미결 `paik` 3번)과 같은 판단으로 nullable — 이미 올라간
클립·안 보낸 클라이언트는 NULL.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2598dc30f0cb"
down_revision: Union[str, Sequence[str], None] = "98f9cbdc74f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "video",
        sa.Column("original_filename", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("video", "original_filename")
