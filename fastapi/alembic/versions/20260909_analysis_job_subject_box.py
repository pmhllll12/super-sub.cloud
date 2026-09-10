"""analysis_job 에 「이 사람으로 분석」 대상 박스를 담는다

Revision ID: 411d1c83e4ca
Revises: 6a0f3d23662c
Create Date: 2026-09-09

미결 `paik` 6번. 분석 화면이 「이 사람으로 분석」에서 받은 박스를 어디로도 못
보냈다 — `POST /videos` 본문에 자리가 없었다. 에이전트 쪽은 이미 열려 있다
(`analyze_s3.py --subject-box x,y,w,h --subject-at-ms`).

## 무엇을 넣나

| 컬럼 | 왜 |
|---|---|
| `analysis_job.subject_box` `json` NULL | 정규화 `[x, y, w, h]`(0~1) 리스트. 🔴 픽셀 아님 |
| `analysis_job.subject_at_ms` `integer` NULL | 그 박스를 그린 영상 시각(ms) |

`video` 가 아니라 `analysis_job` 에 두는 것은 **분석 1회의 대상**이라서다 — 같은
영상을 다시 분석하면 다른 사람을 고를 수 있다. `claim` 이 이미 그 행을 읽으므로
응답에 싣는 것도 여기가 싸다.

## 흐름 (`side`·`focus` 와 같은 축)

```
POST /videos {subject_box, subject_at_ms}   ← 서버가 정규화·기하 검증(422)
   → analysis_job 행에 저장
   → claim 응답에 실림
   → 워커가 --subject-box / --subject-at-ms 로 전달   ← agent 쪽 배선은 별건(미결 6번)
```

## 왜 nullable

🔴 **지정이 없는 것이 정상 경로다** — 「자동으로 고르기」. 옛 행·`analyze=False`·
반려된 클립도 NULL 이다. 둘 중 하나만 찬 상태는 없다(스키마·인터랙터가 막는다).
JSON 값 자체를 DB 제약으로 검사하지 않는 것은 `analysis_job.status` 와 같은 판단.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '411d1c83e4ca'
down_revision: Union[str, Sequence[str], None] = '6a0f3d23662c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "analysis_job", sa.Column("subject_box", sa.JSON(), nullable=True)
    )
    op.add_column(
        "analysis_job", sa.Column("subject_at_ms", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("analysis_job", "subject_at_ms")
    op.drop_column("analysis_job", "subject_box")
