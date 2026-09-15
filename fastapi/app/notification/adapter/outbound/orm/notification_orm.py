"""`notification` 테이블. 부록 D 도메인 ①. 미결 `jin` 35번.

🔴 **다른 컨텍스트가 이 테이블에 씁니다.** `user`의 지인 신청 흐름이 원시 SQL로
직접 INSERT한다(`notification_port.py` 참고) — 그래서 `subject_id`에 FK를 걸지
않는다. `subject_type`마다 가리키는 테이블이 다른데, 걸 수 있는 FK는 하나뿐이라
전부 걸 수 없다. 무결성은 애플리케이션이 책임진다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationOrm(Base):
    __tablename__ = "notification"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    recipient_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # 정본 목록은 `app/notification/domain/rules/notification_rules.py`.
    # 참조 테이블로 안 두는 이유는 그 파일 docstring 참고.
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    # 알림을 유발한 사람. 그 사람이 탈퇴해도 알림 자체(받은 사람 것)는 남아야
    # 하므로 CASCADE 가 아니라 SET NULL.
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    # 이 알림이 가리키는 대상 종류·id. FK 는 안 건다 — 위 docstring 참고.
    subject_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # 폴링(`GET /me/notifications`)이 이 순서로 읽는다 — 최신순 목록의
        # 기본 접근 경로다.
        Index(
            "ix_notification_recipient_created",
            "recipient_user_id",
            "created_at",
        ),
    )
