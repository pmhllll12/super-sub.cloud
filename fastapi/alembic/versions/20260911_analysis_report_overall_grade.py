"""analysis_report 에 overall_grade 컬럼

Revision ID: 8a765b42e48e
Revises: a1c9f7b2e034
Create Date: 2026-09-11

미결 `ho` 28번 (정상호 제기, 사용자 요청). 리포트 읽기 경로가 `score`·`grade`·
`breakdown[].stat` 을 줘야 하는데, `score` 와 `stat` 은 `analysis_metric_value`
에 이미 있지만 총점의 **글자 등급**(A/B/C/D, `result.grade`)은 어디에도 저장하지
않고 있었다.

**새로 계산하지 않는다.** `scoring.aggregate` 가 이미 `grade_bands` 로 낸 값을
그대로 받아 적는다 — 백엔드가 문턱값(85/70/50/0)을 다시 하드코딩하면 루브릭이
그 값을 바꿀 때(지금은 "6종 전부 같다"고만 되어 있다) 조용히 어긋난다.

`total_score` 처럼 `analysis_metric_value` 에 넣지 않는 이유: 그 테이블의
`value` 는 `Numeric` 이라 문자열 등급이 안 들어간다. `analysis_report` 가
분석 단위의 메타(검수 전 여부 등)를 담는 자리라 여기 둔다.

옛 행(이 컬럼이 생기기 전 적재분)은 NULL — 재분석 없이는 못 채운다
(`report.json` 을 다시 읽어야 한다).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a765b42e48e'
down_revision: Union[str, Sequence[str], None] = 'a1c9f7b2e034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'analysis_report',
        sa.Column('overall_grade', sa.String(length=1), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('analysis_report', 'overall_grade')
