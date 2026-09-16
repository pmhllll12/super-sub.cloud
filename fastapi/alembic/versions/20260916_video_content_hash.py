"""video.content_hash·duplicate_of_video_id — ho 41번

Revision ID: 8c1f4a6e9d02
Revises: 5e91b4a7c3d8
Create Date: 2026-09-16

부록 D 도메인 ②. 같은 파일을 다시 올려도 같은 결과가 나오는 결정론적
파이프라인인데, 화면에 안내가 없어 실서버에서 같은 영상이 9번 재업로드되고
9번 같은 사유로 게이트에서 떨어진 사례가 나왔다(`ho` 41번). GPU·S3 낭비를
줄이려고, 등록 때 같은 사용자의 같은 내용(`content_hash`) 영상 중 분석까지
끝난 것이 있으면 새 작업을 안 만들고 그 결과를 등록 응답에 실어 알려준다.

## `content_hash` — S3 ETag

다운로드 없이 이미 하던 `HeadObject`(`size_of`가 부른다)로 얻는다. 이
저장소는 사전 서명 단일 PUT만 쓰므로(상한 200MB, 멀티파트 없음) ETag가
곧 MD5다 — 클라이언트 해싱도 새 S3 호출도 필요 없다.

## `duplicate_of_video_id` — 가짜 `analysis_job`을 안 만드는 이유

재사용을 `analysis_job`을 `queued`를 건너뛰고 바로 `succeeded`/`failed`로
만드는 방식으로 하면 `job_rules.py`가 명시적으로 금지한 것과 같은 모양이
된다("queued 에서 바로 끝내지 않는다" — 워커가 안 집은 작업이 끝난 것처럼
보이면 PER-001이 보려는 `started_at`/`finished_at` 차이가 거짓이 된다).
그래서 이 영상 자신은 작업을 아예 안 만들고, 대신 결과를 빌려온 원본
영상을 가리키기만 한다 — 나중에 이 영상을 다시 읽으면(`GET /videos`
등) `analysis_status`는 정직하게 `None`(작업 없음)이고, 빌려온 결과는
등록 응답 한 번에만 실린다.

## 둘 다 nullable이다

옛 행은 이 컬럼이 생기기 전이라 값이 없다. `duplicate_of_video_id`는
원본이 지워지면 SET NULL로 풀린다 — 이 영상 자체는 지워지면 안 된다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8c1f4a6e9d02"
down_revision: Union[str, Sequence[str], None] = "5e91b4a7c3d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video", sa.Column("content_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "video",
        sa.Column("duplicate_of_video_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_video_duplicate_of_video_id_video",
        "video",
        "video",
        ["duplicate_of_video_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_video_user_content_hash", "video", ["user_id", "content_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_video_user_content_hash", table_name="video")
    op.drop_constraint(
        "fk_video_duplicate_of_video_id_video", "video", type_="foreignkey"
    )
    op.drop_column("video", "duplicate_of_video_id")
    op.drop_column("video", "content_hash")
