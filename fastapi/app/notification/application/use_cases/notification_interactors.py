"""알림 인터랙터."""

from __future__ import annotations

from app.core.errors import ApiError
from app.notification.application.dtos.notification_dto import (
    LIST_LIMIT,
    ListNotificationsQuery,
    MarkNotificationReadCommand,
    NotificationResult,
)
from app.notification.application.ports.input.notification_use_cases import (
    ListNotificationsUseCase,
    MarkNotificationReadUseCase,
)
from app.notification.application.ports.output.notification_port import (
    NotificationPort,
)
from app.notification.application.use_cases.notification_assembler import (
    to_notification_result,
)


class ListNotificationsInteractor(ListNotificationsUseCase):
    def __init__(self, repository: NotificationPort) -> None:
        self._repository = repository

    def __call__(self, query: ListNotificationsQuery) -> list[NotificationResult]:
        notifications = self._repository.list_for_recipient(
            query.recipient_id, unread_only=query.unread_only, limit=LIST_LIMIT
        )
        return [to_notification_result(n) for n in notifications]


class MarkNotificationReadInteractor(MarkNotificationReadUseCase):
    def __init__(self, repository: NotificationPort) -> None:
        self._repository = repository

    def __call__(self, command: MarkNotificationReadCommand) -> NotificationResult:
        notification = self._repository.find_by_id(command.notification_id)
        if notification is None:
            raise ApiError(
                404, "NOTIFICATION_NOT_FOUND", "알림을 찾을 수 없습니다."
            )
        if notification.recipient_user_id != command.actor_id:
            # "없음"과 "권한 없음"을 가른다 — `match`의 `AcceptApplicationInteractor`
            # 와 같은 판단이지만, 여기는 남의 알림 존재 자체가 새어 나가도 될
            # 정보가 아니라서 404 로 통일한다(내 알림 목록에 없던 id 는 처음부터
            # 존재를 몰라야 한다).
            raise ApiError(
                404, "NOTIFICATION_NOT_FOUND", "알림을 찾을 수 없습니다."
            )

        updated = self._repository.mark_read(notification.id)
        return to_notification_result(updated)
