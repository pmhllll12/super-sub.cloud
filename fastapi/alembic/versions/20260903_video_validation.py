"""video validation

Revision ID: c41d7a6b8e02
Revises: 69f3d0e97ffd
Create Date: 2026-09-03

부록 D 도메인 ② 의 빈자리 하나를 채운다. `video` 는 08-28 에 들어갔는데
(`20260828_analysis_domain_tables`) 규격 검사 결과를 담을 곳이 없어 SFR-001 의
"반려 사유를 값으로 기록한다"가 코드에만 있었다.

## 컬럼을 늘리지 않았다

ERD 가 정한 다섯(`id`·`video_id`·`passed`·`reject_reason`·`checked_at`)뿐이다.
잰 값(해상도·길이)을 컬럼으로 두고 싶어지지만, 그러면 **같은 사실이 두 곳에**
남는다 — `video.duration_ms` 와 갈릴 수 있고, 상한이 바뀌면 옛 행의 판정과
값이 서로 안 맞는 상태가 된다. 사유 문장이 그 시점의 값을 품는다.

## 삭제 규칙은 `analysis_job` 과 같게 뒀다

`video_id` 에 `ON DELETE CASCADE` 다. SEC-006 의 삭제 연쇄가 `user -> video` 로
내려오는데(`20260828_cascade_delete_for_personal_data`) 여기서 끊기면 영상이
지워질 때 판정만 남아 외래키 위반으로 삭제가 막힌다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c41d7a6b8e02'
down_revision: Union[str, Sequence[str], None] = '69f3d0e97ffd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "video_validation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["video.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", name="uq_video_validation"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("video_validation")
