"""analysis_job 에 「집중해서 볼 항목」(focus)을 담는다

Revision ID: 9fc8835184c9
Revises: 2088e26b34ac
Create Date: 2026-09-09

미결 `paik` 8번. 분석 화면에서 올린 사람이 **채점 항목**을 고를 수 있게 됐는데
(`www/src/lib/rubricFocus.ts`), 그 값을 워커까지 보낼 자리가 없었다.
`subject_box`(미결 `paik` 6번)와 같은 축 — 「올린 사람이 무엇을 원하는지」다.

## 무엇을 넣나

`analysis_job.focus` `json` NULL — 루브릭 `criteria[].id` 리스트
(예: `["follow_through", "guide_hand"]`). 등록(`POST /videos`)이 받아 넣고,
`claim` 응답에 실려 워커의 `--focus` 로 흘러간다(agent 쪽 `analyze_command` 는
이미 `job.get("focus")` 를 읽는다).

## 흐름 (`subject_box`·`side` 와 같은 축)

```
POST /videos {focus: [...]}   ← 서버가 형식만 검증(비어 있으면 「전체」)
   → analysis_job 행에 저장
   → claim 응답에 실림
   → 워커가 --focus a,b,c 로 전달
```

## 왜 nullable

🔴 **빈 목록 = 「전체적으로」가 기본이자 가장 흔한 경우다** — 실패로 만들지
않는다(미결 `paik` 8번 「하지 말 것」). 옛 행·`analyze=False`·반려된 클립도 NULL.
JSON 값을 DB 제약으로 검사하지 않는 것은 `analysis_job.status` 와 같은 판단.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fc8835184c9'
down_revision: Union[str, Sequence[str], None] = '2088e26b34ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("analysis_job", sa.Column("focus", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("analysis_job", "focus")
