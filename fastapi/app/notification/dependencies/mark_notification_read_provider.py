"""알림 읽음 처리 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.notification.application.ports.input.notification_use_cases import (
    MarkNotificationReadUseCase,
)
from app.notification.application.use_cases.notification_interactors import (
    MarkNotificationReadInteractor,
)
from app.notification.dependencies.notification_repository_provider import (
    NotificationRepositoryDep,
)


def get_mark_notification_read_use_case(
    repository: NotificationRepositoryDep,
) -> MarkNotificationReadUseCase:
    return MarkNotificationReadInteractor(repository)


MarkNotificationReadUseCaseDep = Annotated[
    MarkNotificationReadUseCase, Depends(get_mark_notification_read_use_case)
]
