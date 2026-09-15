"""알림 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# 한 번에 내려주는 최대 개수. 페이지네이션은 없다 — 안 읽은 알림이 이만큼
# 쌓이면 사람이 못 따라가는 게 먼저 문제다.
LIST_LIMIT = 50


@dataclass(frozen=True)
class ListNotificationsQuery:
    recipient_id: UUID
    unread_only: bool = False


@dataclass(frozen=True)
class MarkNotificationReadCommand:
    actor_id: UUID
    notification_id: UUID


@dataclass(frozen=True)
class NotificationResult:
    id: UUID
    type: str
    actor_user_id: UUID | None
    subject_type: str | None
    subject_id: UUID | None
    read_at: datetime | None
    created_at: datetime
