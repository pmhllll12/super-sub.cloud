"""match application

Revision ID: 69f3d0e97ffd
Revises: 3b93fe12219a
Create Date: 2026-09-02

부록 D 도메인 ④ 의 셋째다. 지원(사람 -> 팀)과 제안(팀 -> 사람)을 한 테이블로 담는다.

## 상태 컬럼을 두지 않는다

부록 D.5 가 "매칭 확정은 사람이 한다"를 **스키마로 강제한 것**이 이 테이블이다.
`team_accepted_at` · `user_accepted_at` 을 각각 두고 **둘 다 채워진 것이 확정**이다.
`status` 하나로 두면 확정 조건이 코드에만 남아 DB 만 보고는 알 수 없다.

시작한 쪽도 시각이 말해 준다 — 사람이 지원했으면 `user_accepted_at` 만, 팀이
제안했으면 `team_accepted_at` 만 차 있다. 그래서 `created_at` 을 만들지 않았다.
**ERD 에 없는 컬럼은 늘리지 않는다.**

## 외래키 삭제 규칙은 기본값이다

부록 D.6 이 "match -> match_application -> fitness_score 체인의 삭제 규칙은 스키마
확정 시 일괄로 정한다"고 미뤄 두었다. 여기서 혼자 정하지 않고 기본(RESTRICT)으로 둔다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '69f3d0e97ffd'
down_revision: Union[str, Sequence[str], None] = '3b93fe12219a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "match_application",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("team_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["match.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "user_id", name="uq_match_application"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("match_application")
