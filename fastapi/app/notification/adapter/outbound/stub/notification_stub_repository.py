"""고정 데이터 저장소. `user_stub_repository.py`와 같은 철학이다.

**응답 형태 확인용이다.** 실제로 쌓이고 읽히는지는 DB 테스트
(`tests/notification/adapter/test_notification_db.py`)가 본다. 그래서 `match`·
`review`처럼 인메모리 dict + `reset()`을 두지 않는다 — 여기 알림은 전부 다른
컨텍스트(`user`)가 원시 SQL로 만드므로, 스텁에 "생성" 자체가 없다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.notification.application.ports.output.notification_port import (
    NotificationPort,
)
from app.notification.domain.entities.notification_entity import NotificationEntity

# `app.user.adapter.outbound.stub.user_stub_repository.DEMO_USER_ID`와 같은 값이다
# (컨텍스트끼리 임포트하지 않으므로 값만 복제 — `user_pg_repository.py`의
# `_UNIQUE_VIOLATION`과 같은 판단).
_DEMO_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")
_DEMO_ACTOR_ID = UUID("9a2e5f31-6d70-4c18-b3a9-4e82d7c05a16")
_DEMO_NOTIFICATION_ID = UUID("6e1a2b3c-4d5e-4f60-8a71-2b3c4d5e6f70")

_NOTIFICATION = NotificationEntity(
    id=_DEMO_NOTIFICATION_ID,
    recipient_user_id=_DEMO_USER_ID,
    type="contact_request",
    actor_user_id=_DEMO_ACTOR_ID,
    subject_type="user_contact",
    subject_id=_DEMO_ACTOR_ID,
    read_at=None,
    created_at=datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc),
)


class StubNotificationRepository(NotificationPort):
    def list_for_recipient(
        self, recipient_id: UUID, *, unread_only: bool, limit: int
    ) -> list[NotificationEntity]:
        if recipient_id != _DEMO_USER_ID:
            return []
        items = [_NOTIFICATION]
        if unread_only:
            items = [n for n in items if not n.is_read]
        return items[:limit]

    def find_by_id(self, notification_id: UUID) -> NotificationEntity | None:
        return _NOTIFICATION if notification_id == _DEMO_NOTIFICATION_ID else None

    def mark_read(self, notification_id: UUID) -> NotificationEntity:
        """스텁은 고정 데이터라 저장하지 않는다. 실제 반영은 DB 테스트가 본다."""
        from dataclasses import replace

        return replace(_NOTIFICATION, read_at=datetime.now(timezone.utc))
