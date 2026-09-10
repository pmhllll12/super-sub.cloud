"""analysis_metric_criterion 에 view_dependent 컬럼

Revision ID: a1c9f7b2e034
Revises: efcf961d0051
Create Date: 2026-09-10

미결 `ho` 38번 (정상호 제기, 판단은 정어진). 미결 37번 처방을 넣으면서
`report.json` 의 `result.breakdown[]` 에 `view_dependent` 필드가 하나 늘었다
(schema_version 1.0 → 1.1, minor 라 적재 자체는 안 깨진다).

**값**: `""` · `"metric"` · `"grade"` 셋뿐. 그 항목의 등급이 **촬영 방향에
의존하는가** — `"grade"` 면 "반대편에서 찍혔으면 등급이 달랐다"는 뜻이다.
실측으로 축구 슛 200클립 중 192건(96%)이 `"grade"` 라 드문 값이 아니다.

**왜 저장하나**: `band`·`out_of_band` 와 같은 등급의 **개발 확인용 항목별
메타**다. `analysis_metric_criterion` 이 이미 그 둘을 담고 있고, 여기 두면
"이 등급은 촬영 방향에 갈렸다"를 재분석 없이 되짚을 수 있다(`ho` 28 오버롤
등급 읽기 경로와 결이 같다). 안 두면 나중에 S3 의 `report.json` 을 전수
재파싱해야 채운다.

🔴 **선수 화면 DTO 에는 넣지 않는다** — `band`·`out_of_band` 와 같다.
`efcf961d0051` 이 이미 push·참조돼 있어(미결 27번·MEMORY) 그 파일을 고치지
않고 별도 리비전으로 더한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f7b2e034'
down_revision: Union[str, Sequence[str], None] = 'efcf961d0051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'analysis_metric_criterion',
        sa.Column('view_dependent', sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('analysis_metric_criterion', 'view_dependent')
