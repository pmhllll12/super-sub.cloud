"""analysis_job.job_type + detection_result — ho 44번

Revision ID: d4a8e5f1c3b7
Revises: b3f7a1c9d2e6
Create Date: 2026-09-15

미결 `ho` 44번(검출된 사람 목록을 화면에 주는 경로). 안 (가) — 큐 기반 `detect`
작업, 기존 `analysis_job`의 클레임/폴링 구조를 그대로 재사용한다(정어진 결정,
`agent/scripts/detect_subjects.py`는 이미 있음, 워커 배선은 정상호 몫으로 남음).

`job_type`은 옛 행을 전부 `"analyze"`로 채운다 — 그때는 이 구분이 없었으니
전부 분석 작업이었다. `detection_result`는 `detect` 작업의 결과(`people`·
`ball`)를 담는다 — `subject_box`가 이미 이 테이블에서 JSON을 쓰는 전례를
그대로 따른다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a8e5f1c3b7"
down_revision: Union[str, Sequence[str], None] = "b3f7a1c9d2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_job",
        sa.Column(
            "job_type",
            sa.String(length=20),
            nullable=False,
            server_default="analyze",
        ),
    )
    op.add_column(
        "analysis_job",
        sa.Column("detection_result", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_job", "detection_result")
    op.drop_column("analysis_job", "job_type")
