"""video 에 "프로필에 저장됨" 표시를 담는다

Revision ID: 10f68718757d
Revises: 5db18b239336
Create Date: 2026-09-08

미결 `jin` 24번(영상 수명 주기) 1조각. `/analysis` 분석은 임시로 올라가고
"내 프로필에 리포트 저장"을 눌러야 남는다. `kept=false` 는 그 임시 상태다.

## 왜 기본값이 true 인가

이미 올라간 행과, `/me` 「업로드」 탭(기록용)은 사용자가 명시적으로 올린 것이라
항상 남는다. 임시 상태는 `/analysis` 경로에만 걸리고, 그 전환(`kept = not analyze`)
은 프론트가 `keep` 을 부를 준비가 된 뒤 별도로 켠다(jin 24 5조각). 지금은 전
계층 배선만 하고 동작은 그대로 둔다 — 그래서 신규도 `true` 다.

## 부분 인덱스

스윕(백스톱)이 `WHERE kept=false` 로만 질의한다. 대부분이 `true` 라 부분 인덱스가
작고, 45초마다 도는 질의를 가볍게 유지한다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "10f68718757d"
down_revision: Union[str, Sequence[str], None] = "5db18b239336"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "video",
        sa.Column("kept", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_index(
        "ix_video_provisional",
        "video",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("kept = false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_video_provisional", table_name="video")
    op.drop_column("video", "kept")
