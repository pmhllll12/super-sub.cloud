"""`user` 테이블. 부록 D 도메인 ①.

⚠️ **`user` 는 PostgreSQL 예약어다.** SQLAlchemy 는 예약어를 자동으로 큰따옴표로
감싸므로 ORM 으로 다루는 한 문제가 없다. 다만 psql 에서 손으로 조회할 때는
`select * from "user"` 처럼 따옴표가 필요하다. 테이블 이름은 부록 D 가 정본이라
바꾸지 않는다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserOrm(Base):
    __tablename__ = "user"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 부록 D.7 — 계정 식별. 값 객체 Email 이 생성 시점에 소문자로 정규화하므로
    # 대소문자만 다른 값이 별개 계정이 되지 않는다.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    nickname: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
