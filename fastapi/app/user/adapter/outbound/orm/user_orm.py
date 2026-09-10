"""`user` 테이블. 부록 D 도메인 ①.

⚠️ **`user` 는 PostgreSQL 예약어다.** SQLAlchemy 는 예약어를 자동으로 큰따옴표로
감싸므로 ORM 으로 다루는 한 문제가 없다. 다만 psql 에서 손으로 조회할 때는
`select * from "user"` 처럼 따옴표가 필요하다. 테이블 이름은 부록 D 가 정본이라
바꾸지 않는다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class UserOrm(Base):
    __tablename__ = "user"
    __table_args__ = (
        Index(
            "ix_user_skill_embedding_hnsw",
            "skill_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"skill_embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 부록 D.7 — 계정 식별. 값 객체 Email 이 생성 시점에 소문자로 정규화하므로
    # 대소문자만 다른 값이 별개 계정이 되지 않는다.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    nickname: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # 🔴 토큰 폐기용(SEC-004). 발급한 토큰에 이 값을 실어 두고 검증할 때 대조한다.
    # 값을 올리면 그 사용자의 **기존 토큰이 전부 무효**가 된다.
    #
    # 리프레시 토큰 회전을 도입하지 않은 이유는 `MEMORY.md` 2026-08-27 에 있다 —
    # 우리에게 필요한 것은 갱신이 아니라 **폐기 능력** 하나뿐이었다.
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    # 용병 매칭용 (2026-09-10 마이그레이션 28148877afc0). `MercenaryPort`가 이
    # 테이블 위의 별도 개념(`MercenaryProfileEntity`)으로 다룬다 — `UserPort`에
    # 얹지 않은 이유는 그 포트의 주석 참고.
    #
    # 🔴 `postgresql.ARRAY`를 쓴다(일반 `sqlalchemy.ARRAY`가 아니다) —
    # `.contains()` 같은 PG 전용 연산자가 일반 ARRAY엔 없다(`mercenary_pg_
    # repository.py`의 종목별 포지션 필터가 이걸 쓴다). DDL은 둘 다 같은
    # `character varying[]`라 이 차이만으로는 새 마이그레이션이 필요 없다.
    preferred_positions: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    available_slots: Mapped[list | None] = mapped_column(JSON, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    skill_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_searchable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    skill_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768), nullable=True
    )
