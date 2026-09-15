"""reference_player — paik 29번

Revision ID: f2a6c8b3e9d1
Revises: e7c2a9f4b1d5
Create Date: 2026-09-15

부록 D 도메인 ②. `paik` 29번(선수 영상·관절 결과를 읽는 경로)의 읽는 자리다.

`sport`·`position`·`region`과 같은 이유로 참조 테이블로 둔다 — 지금은 둘뿐
이지만 나중에 늘어날 때 코드 재배포 없이 행만 추가하면 된다. `id`는
`www/src/components/analysis/AnalysisStage.tsx`의 `COMPARE` id(`rovelli`·
`castanheira`)와 그대로 맞춘다.

`report_key`만 들고 영상 파일 자체는 없다 — 선수 원본 영상은 S3에 없다
(EC2 역할이 `videos/` 접두사에 쓰기 권한이 없어 못 올라갔다). `skeleton`은
`report_key`가 가리키는 리포트 안에 이미 있어서 별도 컬럼으로 복제하지
않는다(정어진 판단, `jin` 27번과 같은 결 — S3에 이미 있는 것을 DB에 또
안 둔다).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a6c8b3e9d1"
down_revision: Union[str, Sequence[str], None] = "e7c2a9f4b1d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reference_player",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("report_key", sa.String(1024), nullable=False),
    )
    op.bulk_insert(
        sa.table(
            "reference_player",
            sa.column("id", sa.String),
            sa.column("name", sa.String),
            sa.column("report_key", sa.String),
        ),
        [
            {
                "id": "rovelli",
                "name": "에스테반 로벨리",
                "report_key": "reports/pro/pexels-15436954/report.json",
            },
            {
                "id": "castanheira",
                "name": "티아구 카스탄헤이라",
                "report_key": "reports/pro/pexels-15436958/report.json",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("reference_player")
