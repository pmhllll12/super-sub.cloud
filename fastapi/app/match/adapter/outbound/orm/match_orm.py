"""`match` 테이블. 부록 D 도메인 ④.

🔴 **종목 컬럼이 없다.** `match -> team -> sport_code` 로 결정된다(부록 D.4 —
"중복이자 모순 가능성"으로 명시돼 있다). **여기에 `sport_code` 를 추가하는 순간
팀 종목과 어긋날 수 있는 두 번째 진실이 생긴다.**
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchOrm(Base):
    __tablename__ = "match"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # 주최 팀. `team` 은 `user` 컨텍스트의 테이블이라 **문자열로 참조**한다.
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=False
    )
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    place: Mapped[str] = mapped_column(String(120), nullable=False)
