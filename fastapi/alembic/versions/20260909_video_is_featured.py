"""video 에 「나를 보여주는 대표 영상」 표시를 담는다

Revision ID: 2088e26b34ac
Revises: 411d1c83e4ca
Create Date: 2026-09-09

미결 `paik` 10번. `/me` 의 영상마다 「나를 보여주는 대표 영상」을 고를 수 있게
됐는데(사용자 요청), `video` 에 그 칸이 없어 지금은 브라우저에만 남는다 —
다른 기기·**다른 사람**에게는 안 보인다.

## 무엇을 넣나

| | |
|---|---|
| `video.is_featured` `boolean NOT NULL default false` | 이 클립이 그 사람의 대표인가 |
| 부분 유일 인덱스 `uq_video_featured_per_user` (`user_id` where `is_featured`) | 🔴 **사람당 하나** — 앱이 「세우기 전에 남을 내린다」를 빠뜨려도 둘째가 못 들어간다 |

## 왜 부분 유일 인덱스인가

`is_featured=false` 인 행은 유일 제약에서 빠진다(부분 인덱스 `WHERE is_featured`).
그래서 사람이 클립을 아무리 많이 가져도, `is_featured=true` 는 사람당 최대 하나다.
「대표를 여러 개 허용하지 마세요」(미결 `paik` 10번)를 DB 가 지킨다.

반려된 클립(`video_validation.passed=false`)이 대표가 되지 않게 하는 것은
**앱 규칙**이다(`PATCH /videos/{id}` 인터랙터). 스키마로 걸지 않는 이유는
`analysis_job.status` 값을 제약으로 안 거는 것과 같다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2088e26b34ac'
down_revision: Union[str, Sequence[str], None] = '411d1c83e4ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "video",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.create_index(
        "uq_video_featured_per_user",
        "video",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_featured"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_video_featured_per_user", table_name="video")
    op.drop_column("video", "is_featured")
