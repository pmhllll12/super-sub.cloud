"""`NotificationPort`의 PostgreSQL 구현. 생성은 없다 — 포트 docstring 참고."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.notification.adapter.outbound.mappers.notification_mapper import (
    to_notification_entity,
)
from app.notification.adapter.outbound.orm.notification_orm import NotificationOrm
from app.notification.application.ports.output.notification_port import (
    NotificationPort,
)
from app.notification.domain.entities.notification_entity import NotificationEntity


class NotificationPgRepository(NotificationPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_recipient(
        self, recipient_id: UUID, *, unread_only: bool, limit: int
    ) -> list[NotificationEntity]:
        stmt = select(NotificationOrm).where(
            NotificationOrm.recipient_user_id == recipient_id
        )
        if unread_only:
            stmt = stmt.where(NotificationOrm.read_at.is_(None))
        stmt = stmt.order_by(desc(NotificationOrm.created_at)).limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [to_notification_entity(row) for row in rows]

    def find_by_id(self, notification_id: UUID) -> NotificationEntity | None:
        row = self._session.get(NotificationOrm, notification_id)
        return to_notification_entity(row) if row is not None else None

    def mark_read(self, notification_id: UUID) -> NotificationEntity:
        row = self._session.get(NotificationOrm, notification_id)
        if row.read_at is None:
            row.read_at = datetime.now(timezone.utc)
            self._session.commit()
            self._session.refresh(row)
        return to_notification_entity(row)
