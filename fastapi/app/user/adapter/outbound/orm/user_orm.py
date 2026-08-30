"""`user` 테이블. 부록 D 도메인 ①.

⚠️ **`user` 는 PostgreSQL 예약어다.** SQLAlchemy 는 예약어를 자동으로 큰따옴표로
감싸므로 ORM 으로 다루는 한 문제가 없다. 다만 psql 에서 손으로 조회할 때는
`select * from "user"` 처럼 따옴표가 필요하다. 테이블 이름은 부록 D 가 정본이라
바꾸지 않는다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Uuid
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

    # 🔴 토큰 폐기용(SEC-004). 발급한 토큰에 이 값을 실어 두고 검증할 때 대조한다.
    # 값을 올리면 그 사용자의 **기존 토큰이 전부 무효**가 된다.
    #
    # 리프레시 토큰 회전을 도입하지 않은 이유는 `MEMORY.md` 2026-08-27 에 있다 —
    # 우리에게 필요한 것은 갱신이 아니라 **폐기 능력** 하나뿐이었다.
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
