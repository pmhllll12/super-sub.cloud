"""team_invitation — min 20번

Revision ID: b3e7c92f5a14
Revises: 8c1f4a6e9d02
Create Date: 2026-09-16

부록 D 도메인 ①. 팀이 용병 검색 결과에서 고른 개인을 초대해 데려오는
자리다(`min` 20번). 챗봇 검색(`search_candidates`)은 이미 됐는데 찾은
사람을 실제로 데려오는 길이 없었다 — 동의 없이 바로 `team_member`에
꽂는 것은 안 쓰기로 했고(2026-09-10 박민호 결정), 초대→수락 상태 전이가
필요해 새 테이블을 둔다.

`team_match_request`(팀 대 팀, `match` 컨텍스트)와 상태 전이 모양만
같다 — `team`은 `user` 컨텍스트 테이블이라 `team_member`와 나란히
여기에 둔다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3e7c92f5a14"
down_revision: Union[str, Sequence[str], None] = "8c1f4a6e9d02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "team_invitation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("invited_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["invited_user_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_team_invitation_team", "team_invitation", ["team_id", "status"]
    )
    op.create_index(
        "ix_team_invitation_invited_user",
        "team_invitation",
        ["invited_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_team_invitation_invited_user", table_name="team_invitation")
    op.drop_index("ix_team_invitation_team", table_name="team_invitation")
    op.drop_table("team_invitation")
