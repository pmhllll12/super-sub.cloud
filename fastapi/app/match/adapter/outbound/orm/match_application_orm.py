"""`match_application` 테이블. 부록 D 도메인 ④.

🔴 **상태 컬럼이 없다.** 양측 수락 시각을 각각 두고 **둘 다 채워진 것을 확정으로
본다**(부록 D.5 — "매칭 확정은 사람이 한다"). 단일 상태값(`status`)으로 두면 확정
조건이 코드에만 남아 DB 만 보고는 무엇이 확정인지 알 수 없다.

**시작한 쪽도 시각이 말해 준다.**

| 채워진 것 | 뜻 |
|---|---|
| `user_accepted_at` 만 | 사람이 **지원**했고 팀이 아직 안 받았다 |
| `team_accepted_at` 만 | 팀이 **제안**했고 사람이 아직 안 받았다 |
| 둘 다 | 확정 |

그래서 `created_at` 이 없다 — **부록 D 의 ERD 에 없는 컬럼을 늘리지 않는다.**
시작 시각은 둘 중 먼저 찬 값이다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchApplicationOrm(Base):
    __tablename__ = "match_application"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    match_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("match.id"), nullable=False
    )
    # `user` 는 `user` 컨텍스트의 테이블이라 **문자열로 참조**한다.
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    team_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # 부록 D.7 — 경기당 1인 1회 지원.
        UniqueConstraint("match_id", "user_id", name="uq_match_application"),
    )
