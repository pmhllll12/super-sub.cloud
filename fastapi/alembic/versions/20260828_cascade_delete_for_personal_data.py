"""cascade delete for personal data

Revision ID: 02ae7ff7d9da
Revises: 1d3833241441
Create Date: 2026-08-28 16:26:58.692403

부록 D.6 의 삭제 연쇄를 **외래키 규칙으로** 건다(SEC-006). 코드에 두면 삭제 경로가
늘 때마다 빠뜨리므로, D.5 가 말한 대로 스키마에서 강제한다.

`user_credential` 과 `user_identity` 는 이미 CASCADE 라 여기 없다.

**정의 테이블은 넣지 않는다** — `user_title.title_code → title_definition`,
`analysis_metric_value.metric_code → metric_definition`, `team_member.team_id → team`.
개인 데이터가 아니라 참조하는 목록이고, 사람이 지워졌다고 사라지면 안 된다.

🔴 `--autogenerate` 는 기존 외래키의 삭제 규칙 변경을 잡지 못한다. 그래서 손으로 썼다.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '02ae7ff7d9da'
down_revision: Union[str, Sequence[str], None] = '1d3833241441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (제약 이름, 테이블, 컬럼, 참조 테이블)
_CASCADES = [
    ("player_card_user_id_fkey", "player_card", "user_id", "user"),
    ("user_title_user_id_fkey", "user_title", "user_id", "user"),
    ("team_member_user_id_fkey", "team_member", "user_id", "user"),
    ("video_user_id_fkey", "video", "user_id", "user"),
    ("analysis_job_video_id_fkey", "analysis_job", "video_id", "video"),
    (
        "analysis_metric_analysis_job_id_fkey",
        "analysis_metric",
        "analysis_job_id",
        "analysis_job",
    ),
    (
        "analysis_metric_value_analysis_metric_id_fkey",
        "analysis_metric_value",
        "analysis_metric_id",
        "analysis_metric",
    ),
    (
        "analysis_report_analysis_metric_id_fkey",
        "analysis_report",
        "analysis_metric_id",
        "analysis_metric",
    ),
]


def upgrade() -> None:
    """Upgrade schema."""
    for name, source, column, target in _CASCADES:
        op.drop_constraint(name, source, type_="foreignkey")
        op.create_foreign_key(
            name, source, target, [column], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for name, source, column, target in _CASCADES:
        op.drop_constraint(name, source, type_="foreignkey")
        op.create_foreign_key(name, source, target, [column], ["id"])
