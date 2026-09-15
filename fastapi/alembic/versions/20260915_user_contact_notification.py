"""user_contact + notification, user 검색 노출·닉네임 유일

Revision ID: b3f7a1c9d2e6
Revises: c4f1a6e29b73
Create Date: 2026-09-15

부록 D 도메인 ①. 미결 `jin` 35번(상호 지인 신청·수락 + 폴링 알림).

## `user.nickname` 유일 제약

운영 DB에 중복 0건 확인 후 추가(2026.09.15). 지인 검색(`GET /users/search`)이
닉네임으로 사람을 특정해야 하므로 유일해야 뜻이 선다.

## `user.is_nickname_searchable`

용병 매칭의 `is_searchable`과는 다른 개념이다 — 그쪽은 AI 추천 후보 노출,
이건 지인 검색 노출이다. 기본값 `true`(전체 검색 가능).

## `user_contact`는 상호 관계, `notification`은 알림 저장소

`user_contact.note`는 신청자만의 개인 메모라 상대에게는 안 보여준다(응용 계층
책임). `notification`은 다른 컨텍스트가 원시 SQL로 쓴다 — `subject_id`에 FK를
안 거는 이유는 `app/notification/adapter/outbound/orm/notification_orm.py`
docstring 참고.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f7a1c9d2e6"
down_revision: Union[str, Sequence[str], None] = "c4f1a6e29b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_nickname_searchable",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.create_unique_constraint("uq_user_nickname", "user", ["nickname"])

    op.create_table(
        "user_contact",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "requester_user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "requester_user_id", "target_user_id", name="uq_user_contact_pair"
        ),
    )

    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "recipient_user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject_type", sa.String(40), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_notification_recipient_created",
        "notification",
        ["recipient_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_recipient_created", table_name="notification")
    op.drop_table("notification")
    op.drop_table("user_contact")
    op.drop_constraint("uq_user_nickname", "user", type_="unique")
    op.drop_column("user", "is_nickname_searchable")
