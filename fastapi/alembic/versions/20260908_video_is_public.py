"""video 에 공개 여부를 담는다

Revision ID: 5d010279c679
Revises: c9e15a3b7d24
Create Date: 2026-09-08

미결 `paik` 5번(1+2 조각). 홈의 영상 모음이 화면 안의 붙박이 목록이라, `/me` 에서
올린 클립을 공개로 돌려도 그 브라우저의 `localStorage` 에만 남았다. 다른 기기·
다른 사람에게 보이려면 공개 여부가 서버에 있어야 한다.

## 왜 기본값이 거짓인가

🔴 이미 올라간 클립이 전부 남에게 보이면 안 된다. `server_default` 를 `false` 로
두어 기존 행도 비공개로 채운다. 앱은 등록할 때 늘 값을 정하므로(`is_public` 는
`VideoOrm` 의 Python 기본값도 `False`) 이 기본값에 기대는 것은 마이그레이션
순간의 기존 행뿐이다.

## 왜 불리언인가

"공개/비공개" 두 값이다. `analysis_job.status` 처럼 늘어날 여지가 없어 문자열로
둘 이유가 없다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5d010279c679"
down_revision: Union[str, Sequence[str], None] = "c9e15a3b7d24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "video",
        sa.Column(
            "is_public", sa.Boolean(), server_default="false", nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("video", "is_public")
