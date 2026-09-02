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
    # 🔴 `sport` 테이블이 생겼지만(2026-09-01) **여기에는 외래키를 걸지 않았다** —
    # 부록 D.3 의 외래키 표에 `team.sport_code → sport` 가 없다. 문서에 없는 제약을
    # 임의로 늘리지 않는다. 값은 `sport.code` 와 같은 것을 쓴다(데이터는 함께 옮겼다).
    sport_code: Mapped[str] = mapped_column(String(20), nullable=False)
