"""알림 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.notification.application.dtos.notification_dto import (
    ListNotificationsQuery,
    MarkNotificationReadCommand,
    NotificationResult,
)


class ListNotificationsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListNotificationsQuery) -> list[NotificationResult]:
        """내 알림 목록. 최신순, 최대 `LIST_LIMIT`."""


class MarkNotificationReadUseCase(ABC):
    @abstractmethod
    def __call__(self, command: MarkNotificationReadCommand) -> NotificationResult:
        """읽음 처리. **내 알림만** 가능하다."""
