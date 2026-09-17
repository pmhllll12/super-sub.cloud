"""analysis_report.card_notes — paik 33번 / ho 50번

Revision ID: a7d5e0f34c19
Revises: f1c83b0d59a4
Create Date: 2026-09-17

추천 판(`SquadSuggest`)의 후보 카드에 붙는 **불릿 한두 줄**이다. 지금은 화면
붙박이 문자열이고(`FLAVOR`), 봉투에는 2026-09-16부터 실려 온다
(`result.card.notes`, `schema_version` 1.5 — `ho` 50번).

## 여기(`analysis_report`)에 담는 이유

`summary` 와 **같은 층**이다 — 분석 1회당 하나이고, 등급이 정해지면 코드가
짓는 문장이다(모델이 쓴 `evidence` 는 항목별이라 `analysis_metric_criterion`
에 있다). 부록 D.7 이 이 테이블에 「지표 집합당 1건」을 정해 둔 것과도 맞는다.

## `card.title` 은 안 받는다

봉투에는 함께 오지만 **추천 카드가 안 쓴다**(`ho` 50번 결정 — 이름 아래
한 줄은 사람이 적은 호칭이 채운다, `paik` 36번). 항목별 칭호는 이미
`analysis_metric_criterion.title` 에 있으므로 여기 또 담으면 같은 값이 두
곳에 생긴다. **필요해지면 그때 받는다** — 봉투는 안 바뀐다.

## JSON 인 이유

한 줄 또는 두 줄이고 「두 줄을 채우려고 지어내지 않는다」가 규칙이라
**개수가 값의 일부**다. 두 컬럼으로 쪼개면 "둘째 줄이 없다"와 "둘째 줄이
빈 문자열이다"가 섞인다. 옛 행과 `card` 없는 봉투는 NULL 이다.

🔴 **NULL 은 "분석이 없다"가 아니라 "이 칸이 없는 봉투로 적재됐다"** 이다 —
화면은 그때 불릿 줄을 안 그리면 된다(빈 카드를 내보내지 않는 것은 에이전트
쪽에서 이미 막았다).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7d5e0f34c19"
down_revision: Union[str, Sequence[str], None] = "f1c83b0d59a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_report", sa.Column("card_notes", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("analysis_report", "card_notes")
