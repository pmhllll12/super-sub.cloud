"""`team` 테이블. 부록 D 도메인 ①."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamOrm(Base):
    __tablename__ = "team"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    region: Mapped[str] = mapped_column(String(60), nullable=False)
    # 부록 D 의 sport 코드(현재 futsal·baseball 2행). sport 테이블이 생기면
    # 여기에 외래키를 건다 — 지금은 그 테이블이 없어 코드 문자열로 둔다.
    sport_code: Mapped[str] = mapped_column(String(20), nullable=False)
