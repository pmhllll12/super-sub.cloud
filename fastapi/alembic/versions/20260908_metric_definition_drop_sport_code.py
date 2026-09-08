"""metric_definition 에서 sport_code 를 없앤다 (적재 규격 A안)

Revision ID: 5db18b239336
Revises: 4319b9d12617
Create Date: 2026-09-08

미결 `jin` 1번 — A안 (`api-contract.md` 3-1 「✅ 결정 — A안」, 정상호 2026-09-08).
지표는 물리량이라 종목과 무관하다. 어느 종목에서 쓰는지는 루브릭이 안다.
루브릭 6개에서 지표 11개 중 7개가 종목을 넘나든다 — `code` 하나로 정의하는 것이
맞다. `metric_definition` 은 아직 0 행이라(적재가 이 결정에 막혀 있었다) 컬럼을
지우는 것으로 끝난다. `sport_code` 에는 외래키가 없었다(`20260901_sport_and_position`
이 A안 대비로 일부러 걸지 않았다).

부록 D.3 의 `metric_definition` 외래키 표 수정은 박민호(미결 `ho` 구역) — 공개
제안서라 여기서 손대지 않는다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5db18b239336"
down_revision: Union[str, Sequence[str], None] = "4319b9d12617"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("metric_definition", "sport_code")


def downgrade() -> None:
    """Downgrade schema.

    되돌리면 `20260828` 이 만든 그대로 `NOT NULL` 로 다시 세운다. 그 시점에 행이
    있으면 채울 값이 없어 실패한다 — A안을 되돌린다는 것은 종목 정보를 어디선가
    다시 가져온다는 뜻이라, 그건 데이터 마이그레이션으로 따로 다뤄야 한다.
    """
    op.add_column(
        "metric_definition",
        sa.Column("sport_code", sa.String(length=20), nullable=False),
    )
