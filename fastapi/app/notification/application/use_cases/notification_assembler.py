"""엔티티 → `NotificationResult` 조립."""

from __future__ import annotations

from app.notification.application.dtos.notification_dto import NotificationResult
from app.notification.domain.entities.notification_entity import NotificationEntity


def to_notification_result(n: NotificationEntity) -> NotificationResult:
    return NotificationResult(
        id=n.id,
        type=n.type,
        actor_user_id=n.actor_user_id,
        subject_type=n.subject_type,
        subject_id=n.subject_id,
        read_at=n.read_at,
        created_at=n.created_at,
    )
