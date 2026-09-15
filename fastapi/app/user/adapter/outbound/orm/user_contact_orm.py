"""`user_contact` 테이블. 부록 D 도메인 ①. 미결 `jin` 35번.

상호 관계다 — `requester_user_id`가 신청했고, `accepted_at`이 채워지면 **양쪽 다**
서로를 지인 목록에서 본다. 방향이 있는 이유는 "누가 시작했나"와 `note`(신청자의
개인 메모)를 구분해야 해서다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserContactOrm(Base):
    __tablename__ = "user_contact"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    requester_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    target_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # 신청자만의 개인 메모("같은 동네" 등). 상대방에게는 안 보여준다
    # (`UserContactSummary` 참고) — 신청 사유를 공개하는 것과는 다른 판단이다.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # null 이면 대기중이다 — 상태 컬럼 대신 시각으로 읽는다(부록 D.5 와 같은 판단).
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 같은 방향으로 중복 신청 방지. 반대 방향(B→A) 중복은 유스케이스가
        # `find_contact`(방향 무관 조회)로 막는다 — DB 제약만으로는 A→B, B→A
        # 두 행을 막을 수 없다.
        UniqueConstraint(
            "requester_user_id", "target_user_id", name="uq_user_contact_pair"
        ),
    )
