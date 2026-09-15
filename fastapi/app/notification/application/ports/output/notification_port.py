"""출력 포트 — 알림 조회·읽음 처리.

**생성은 이 포트에 없다.** 알림은 그것을 유발한 컨텍스트(`user`의 지인 신청 등)가
원시 SQL(`table()`/`column()`)로 직접 넣는다 — 여기 `create` 메서드를 두고 다른
컨텍스트가 이 포트를 의존성으로 받게 하면, 그 컨텍스트가 이 컨텍스트의
애플리케이션 계층을 알아야 해서 결합이 오히려 세진다. `match`가 남의 테이블을
**읽을 때** 쓰는 경계 판단을 **쓰기**에도 그대로 적용한 것이다
(`app/user/adapter/outbound/pg/user_pg_repository.py` 참고).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.notification.domain.entities.notification_entity import NotificationEntity


class NotificationPort(ABC):
    @abstractmethod
    def list_for_recipient(
        self, recipient_id: UUID, *, unread_only: bool, limit: int
    ) -> list[NotificationEntity]:
        """최신순."""

    @abstractmethod
    def find_by_id(self, notification_id: UUID) -> NotificationEntity | None: ...

    @abstractmethod
    def mark_read(self, notification_id: UUID) -> NotificationEntity:
        """읽음 처리. 이미 읽었으면 `read_at`을 덮어쓰지 않고 그대로 돌려준다(멱등)."""
