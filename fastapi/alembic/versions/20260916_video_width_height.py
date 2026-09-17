"""video.width·height — paik 15번

Revision ID: 3f8a1c6d2b90
Revises: 704781aa7d4e
Create Date: 2026-09-16

부록 D 도메인 ②. 공개 영상 목록(`GET /videos/public`)이 화면 비율을 미리 알아야
한다(`paik` 15번) — 영상 모음이 실제 파일을 읽어서 비율을 알아내면 그 순간 칸
크기가 바뀌어 화면이 덜컥거린다.

## 왜 이제 와서 저장하나

`width`·`height`는 등록(`POST /videos`) 때부터 받고 있었다 — 규격 검사
(`video_rules.reject_reason`)에만 쓰고 저장은 안 했다. 클라이언트가 잰 값을
서버가 다시 재려면 원본을 내려받아야 하는데 그건 PER-002(업로드·재생이 앱
서버를 지나지 않는다)가 무너진다.

## 둘 다 nullable이다

옛 등록분은 이 컬럼이 생기기 전이라 값이 없다 — **0으로 채우지 않는다**(안
잰 것과 낮은 것은 다르다, `ho` 21번과 같은 판단). 화면은 `null`이면 기존
동작(16:9 가정)을 그대로 쓰면 된다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3f8a1c6d2b90"
down_revision: Union[str, Sequence[str], None] = "704781aa7d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("video", sa.Column("height", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("video", "height")
    op.drop_column("video", "width")
