"""user_custom_title — paik 36번

Revision ID: d7b2f1a4c8e5
Revises: c5a81d0e6b73
Create Date: 2026-09-16

부록 D 도메인 ③. 팀이 방향을 뒤집었다(2026-09-16) — **호칭은 분석이 주는
것이 아니라 사용자 본인이 적는다.** 근거는 "참이든 거짓이든 경기 후 리뷰로
남으니 상관없다"였다. 신뢰는 호칭이 아니라 리뷰가 떠받친다.

그래서 `paik` 32번(분석이 `user_title` 을 붙이게 해 달라)은 ⛔ 로 닫혔고,
대신 **사람이 적는 칸**이 필요해졌다(`paik` 36번).

## `user_title` 과 다른 테이블인 이유

저쪽은 `title_definition` 의 **코드만** 받는다(정의 테이블 참조). 이건
자유 문자열이라 섞으면 `title_code` 를 nullable 로 풀어야 하고, 그러면
"부여된 것만 행으로 존재한다"는 `user_title` 의 뜻이 흐려진다.

🔴 `title_definition` 에 행을 늘리는 방식은 안 쓴다 — 사람마다 다른 문장이라
정의 테이블이 사용자 수만큼 불어난다(`paik` 36번의 「하지 말 것」).

## 상한은 앱이 막는다

길이 20자(카드 한 줄과 같다)는 컬럼으로, **개수 3개는 앱 규칙**으로 건다
(`card_rules.normalize_custom_titles`). 개수를 DB 제약으로 걸면 상한이
바뀔 때 마이그레이션이 필요해진다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7b2f1a4c8e5"
down_revision: Union[str, Sequence[str], None] = "c5a81d0e6b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_custom_title",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_custom_title_user", "user_custom_title", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_custom_title_user", table_name="user_custom_title")
    op.drop_table("user_custom_title")
