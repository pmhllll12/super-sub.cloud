"""match.opponent_team_id + team_match_request — paik 17번

Revision ID: a9d3f7c1b6e2
Revises: f2a6c8b3e9d1
Create Date: 2026-09-15

부록 D 도메인 ④. 팀이 팀에게 경기를 거는 흐름(`paik` 17번) — 개인이 경기에
지원하는 `match_application`과는 주체·승인자가 다르다.

## `match.opponent_team_id`

찼으면 팀 대 팀으로 **확정된** 경기다. `team_match_request` 수락으로만
채워진다. 이런 경기는 양쪽 스쿼드가 이미 찬 전제라 `match_position_need`
(모집)가 필요 없다 — 있어도 막지 않지만 만드는 코드 경로를 새로 열지
않았다.

## `team_match_request` — 상태를 단일 문자열로

`match_application`은 양측 수락 시각 쌍을 쓰지만(어느 쪽이 먼저 시작했는지가
뜻을 가져서), 여기는 항상 신청 팀이 먼저 걸고 대상 팀만 답하는 **비대칭**
흐름이라 `status`(`pending`/`accepted`/`rejected`/`cancelled`) 하나로
충분하다 — `analysis_job.status`와 같은 판단(DB 제약 없이, 단계가 늘 때
마이그레이션 불필요).

수락 시 `match_id`가 채워진다. `match`가 지워져도(과거 경기 정리 등) 신청
이력은 남아야 하므로 `ON DELETE SET NULL`.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9d3f7c1b6e2"
down_revision: Union[str, Sequence[str], None] = "f2a6c8b3e9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "match",
        sa.Column(
            "opponent_team_id",
            sa.Uuid(),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
    )

    op.create_table(
        "team_match_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "requester_team_id",
            sa.Uuid(),
            sa.ForeignKey("team.id"),
            nullable=False,
        ),
        sa.Column(
            "target_team_id",
            sa.Uuid(),
            sa.ForeignKey("team.id"),
            nullable=False,
        ),
        sa.Column("proposed_played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposed_place", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "match_id",
            sa.Uuid(),
            sa.ForeignKey("match.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_team_match_request_requester",
        "team_match_request",
        ["requester_team_id", "status"],
    )
    op.create_index(
        "ix_team_match_request_target",
        "team_match_request",
        ["target_team_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_team_match_request_target", table_name="team_match_request"
    )
    op.drop_index(
        "ix_team_match_request_requester", table_name="team_match_request"
    )
    op.drop_table("team_match_request")
    op.drop_column("match", "opponent_team_id")
