"""`no_show` 테이블. 부록 D 도메인 ⑤ — 불참·지각 기록.

🔴 **`review` 와 이어지지 않는다.** `report` 와 같은 이유다 — 제재는 평가와 분리
한다(3.5).

⚠️ **누가 기록했는지를 담는 컬럼이 없다.** 부록 D 에 없어서 늘리지 않았다.
"주장만 기록할 수 있다"로 좁히려면 **응용 계층이 막아야 한다** — 패킷 B 문서의
「정해야 할 것」에 있고 아직 안 정해졌다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoShowOrm(Base):
    __tablename__ = "no_show"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    match_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("match.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 부록 D.7 — 경기당 1인 1건.
        UniqueConstraint("match_id", "user_id", name="uq_no_show_once_per_match"),
    )
