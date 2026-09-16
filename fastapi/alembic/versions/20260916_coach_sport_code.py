"""coach.sport_code — paik 14번

Revision ID: 704781aa7d4e
Revises: a9d3f7c1b6e2
Create Date: 2026-09-16

부록 D 도메인 ⑥. `market/coaches` 화면의 종목 필터가 걸리게 하는 최소 컬럼이다
(`paik` 14번, 박민호 결정 2026-09-11).

## 다대다가 아니라 단일 컬럼이다

`www/src/lib/market.ts`의 `Coach.sport`가 이미 단일값(`SportCode`)으로
모델링돼 있어 코치가 여러 종목을 겸하는 경우를 지금 다룰 근거가 없다.
`video.sport_code`·`position.sport_code`와 같은 패턴이다.

## NOT NULL로 바로 건다

`coach` 테이블은 아직 0행이라(2026-09-16 실측) 백필이 필요 없다 — 나중에 행이
쌓인 뒤 이 컬럼을 또 손대면 그때는 백필 단계가 필요해진다.

## 가격·소개 문장·후기 등은 이번 범위 밖

`paik` 14번 본문이 명시한 대로 이번엔 `sport_code` 하나만 넣는다. 나머지 mock
필드는 화면·계약을 한 번에 정하는 별도 작업이다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "704781aa7d4e"
down_revision: Union[str, Sequence[str], None] = "a9d3f7c1b6e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "coach",
        sa.Column("sport_code", sa.String(length=20), nullable=False),
    )
    op.create_foreign_key(
        "fk_coach_sport_code_sport",
        "coach",
        "sport",
        ["sport_code"],
        ["code"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_coach_sport_code_sport", "coach", type_="foreignkey")
    op.drop_column("coach", "sport_code")
