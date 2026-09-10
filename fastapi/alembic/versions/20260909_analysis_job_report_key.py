"""analysis_job 에 리포트 자리(report_key)를 담는다

Revision ID: 9d4e88f5b6c2
Revises: 2598dc30f0cb
Create Date: 2026-09-09

미결 `paik` 11번. 워커가 분석을 끝내면 리포트를 S3 에 쓰는데, **그 자리를
완료 보고에 실을 칸이 없었다.** 백엔드가 계산으로 찾을 수 없다 — 자리 규칙
(`analyze_s3` 의 `report_targets`)이 워커 안에만 있고, 파일 이름에 분석 시각이
붙어 같은 영상을 두 번 돌리면 파일이 둘이 된다.

그래서 완료 보고(`PATCH /internal/analysis-jobs/{id}`)가 **버킷 상대 S3 키**를
함께 싣고(예: `reports/<user_id>/<video_id>/report.json`), 여기가 그 받는 칸이다.
paik 7번(리포트 읽는 경로)이 이 값으로 무엇을 읽을지 정한다.

## 왜 nullable 인가

- 옛 행: 이 칸이 생기기 전에 끝난 작업엔 값이 없다.
- 실패(`failed`)한 작업: 가리킬 리포트가 없다 — 인터랙터가 `succeeded` 가
  아니면 `None` 으로 걸러 넘긴다.
- 워커가 자리를 못 실어도(리포트가 다른 버킷 등) 분석은 성공한 것이라 보고
  자체는 통과한다. 화면이 리포트를 못 찾을 뿐이다.

## 왜 String(1024)

S3 객체 키의 한계다. 실제 값은 `reports/<uuid>/<uuid>/report.json` 로 100자
안쪽이지만, 자리 규칙의 정본이 워커라 백엔드가 길이를 좁게 잡아 거절하면
그쪽이 규칙을 못 바꾼다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d4e88f5b6c2'
down_revision: Union[str, Sequence[str], None] = '2598dc30f0cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "analysis_job",
        sa.Column("report_key", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("analysis_job", "report_key")
