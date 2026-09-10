"""add mercenary matching fields to users/profiles

Revision ID: 28148877afc0
Revises: 9fc8835184c9
Create Date: 2026-09-10

주의:
- 대상 테이블명이 `users`라고 가정했었으나, 이 저장소의 실제 테이블명은
  `user`(단수, `app/user/adapter/outbound/orm/user_orm.py`)라 바로잡았습니다.
- pgvector 확장(`vector`)이 이미 활성화되어 있다고 가정합니다. 🔴 이 문서에도
  그 SQL 구문을 그대로 적지 않습니다 — `TestMigrationPrivileges`가 그 글자를
  글자 그대로(주석 포함) 찾아서 막습니다. 이 저장소엔 `moneyball_players`
  테이블이 없고 이 확장을 쓰는 다른 마이그레이션도 없지만, 로컬 DB 확인
  결과 그 확장 자체는 이미 설치돼 있었습니다(환경 준비 단계에서 슈퍼유저가
  만든 것, `docs/deployment.md`). 운영 DB도 같은 절차를 거쳤는지는 배포
  전에 확인이 필요합니다.
- embedding 컬럼 차원은 768로 맞췄습니다. 임베딩 모델을 바꿀 경우 이 숫자도
  함께 바꿔야 합니다.
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "28148877afc0"
down_revision = "9fc8835184c9"
branch_labels = None
depends_on = None

TABLE_NAME = "user"


def upgrade() -> None:
    op.add_column(
        TABLE_NAME,
        sa.Column("preferred_positions", sa.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("available_slots", sa.JSON(), nullable=True),
        # 예: [{"day": "SAT", "start": "18:00", "end": "21:00"}, ...]
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("location", sa.String(), nullable=True),
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("skill_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        TABLE_NAME,
        sa.Column(
            "is_searchable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        # 포지션/가능시간을 다 채운 유저만 True로 바꿔 검색 대상에 포함시킴
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("skill_embedding", Vector(768), nullable=True),
    )

    # HNSW 인덱스 — moneyball_players와 동일한 방식(코사인 유사도)으로 생성
    # 🔴 `user`는 PostgreSQL 예약어라 반드시 큰따옴표로 인용해야 한다
    # (add_column 등 SQLAlchemy DDL은 자동으로 인용하지만, 이 raw SQL은 안 한다).
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{TABLE_NAME}_skill_embedding_hnsw
        ON "{TABLE_NAME}"
        USING hnsw (skill_embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_skill_embedding_hnsw")
    op.drop_column(TABLE_NAME, "skill_embedding")
    op.drop_column(TABLE_NAME, "is_searchable")
    op.drop_column(TABLE_NAME, "skill_summary")
    op.drop_column(TABLE_NAME, "location")
    op.drop_column(TABLE_NAME, "available_slots")
    op.drop_column(TABLE_NAME, "preferred_positions")
