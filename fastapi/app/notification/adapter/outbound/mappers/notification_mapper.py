"""ORM 행 ↔ 도메인 엔티티. `user_mapper.py`와 같은 이유로 순수 함수로 뺀다."""

from __future__ import annotations

from app.notification.adapter.outbound.orm.notification_orm import NotificationOrm
from app.notification.domain.entities.notification_entity import NotificationEntity


def to_notification_entity(row: NotificationOrm) -> NotificationEntity:
    return NotificationEntity(
        id=row.id,
        recipient_user_id=row.recipient_user_id,
        type=row.type,
        actor_user_id=row.actor_user_id,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        read_at=row.read_at,
        created_at=row.created_at,
    )
