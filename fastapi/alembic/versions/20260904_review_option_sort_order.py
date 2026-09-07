"""review_option 에 노출 순서를 담는다

Revision ID: b7c41e2f9a08
Revises: a3d0764cefa5
Create Date: 2026-09-04

`20260903_review_trust_tables` 가 "순서가 화면 노출 순서다"라고 적었지만 **담을
컬럼이 없었다.** SQL 은 `ORDER BY` 없이 행 순서를 보장하지 않는다 — 갓 적재한
직후에는 우연히 맞게 나와서 문제가 안 드러난다. 실제로 `label` 하나를 `UPDATE`
하자 그 행이 맨 끝으로 갔다(2026-09-04 확인, PostgreSQL 이 갱신 행을 힙 뒤에 다시
쓴다).

## 왜 `ORDER BY category, code` 로 안 풀었나

카테고리 알파벳순은 `caution` → `manner` → `repeat` → `skill` 이라 **주의 항목이
맨 앞에** 온다. 의도한 순서(매너 · 실력 · 재매칭 · 주의)와 다르다. 코드순도
마찬가지다 — `manner_communication` 이 `manner_time` 보다 앞선다.

## 왜 코드에 순서를 박지 않았나

파이썬에 목록을 두면 **마이그레이션과 두 곳이 된다.** 선택지를 하나 늘릴 때
양쪽을 고쳐야 하고, 한쪽만 고치면 새 항목이 조용히 빠지거나 순서가 어긋난다.

🔴 **부록 D 의 `review_option` 에는 이 컬럼이 없다.** ERD 를 고쳐야 하고, 그것은
문서 담당의 일이라 미결 항목으로 올렸다(`jin` 구역).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c41e2f9a08"
down_revision: Union[str, Sequence[str], None] = "a3d0764cefa5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# `20260903_review_trust_tables` 가 넣은 순서 그대로다. 10 씩 띄우는 것은 나중에
# 사이에 하나 끼울 때 전부 다시 매기지 않기 위해서다.
_ORDER = [
    ("manner_time", 10),
    ("manner_respect", 20),
    ("manner_communication", 30),
    ("skill_above_expected", 40),
    ("skill_position_fit", 50),
    ("skill_teamplay", 60),
    ("repeat_yes", 70),
    ("caution_position_mismatch", 80),
    ("caution_would_not_repeat", 90),
]


def upgrade() -> None:
    """Upgrade schema."""
    # 🔴 기존 행이 있으므로 NOT NULL 을 바로 걸 수 없다. 채우고 나서 조인다.
    op.add_column(
        "review_option", sa.Column("sort_order", sa.Integer(), nullable=True)
    )

    option = sa.table(
        "review_option", sa.column("code", sa.String), sa.column("sort_order", sa.Integer)
    )
    for code, order in _ORDER:
        op.execute(
            option.update().where(option.c.code == code).values(sort_order=order)
        )

    # 목록에 없는 코드가 남아 있으면(누가 손으로 넣었다면) 뒤로 보낸다 —
    # NULL 이 남으면 다음 줄에서 마이그레이션이 죽는다.
    op.execute(option.update().where(option.c.sort_order.is_(None)).values(sort_order=999))

    op.alter_column("review_option", "sort_order", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("review_option", "sort_order")
