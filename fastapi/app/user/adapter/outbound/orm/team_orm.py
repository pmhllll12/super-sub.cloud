"""`team` 테이블. 부록 D 도메인 ①."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid
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
    # 해체 시각(`paik` 35번). NULL 이면 살아 있는 팀이다.
    #
    # 🔴 팀을 지우지 않고 표시만 하는 이유: `team` 을 참조하는 외래키가 아홉이고
    # 그중 다섯이 NO ACTION 인데(`match` 둘·`squad`·`team_match_request` 둘·
    # `team_member`) **부록 D.6 이 팀 삭제 연쇄를 정하지 않았다.** 문서에 없는
    # 규칙을 스키마로 만들지 않는다 — `team_member.left_at` 과 같은 판단이다.
    disbanded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
