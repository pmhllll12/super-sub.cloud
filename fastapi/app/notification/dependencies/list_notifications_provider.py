"""알림 목록 유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.notification.application.ports.input.notification_use_cases import (
    ListNotificationsUseCase,
)
from app.notification.application.use_cases.notification_interactors import (
    ListNotificationsInteractor,
)
from app.notification.dependencies.notification_repository_provider import (
    NotificationRepositoryDep,
)


def get_list_notifications_use_case(
    repository: NotificationRepositoryDep,
) -> ListNotificationsUseCase:
    return ListNotificationsInteractor(repository)


ListNotificationsUseCaseDep = Annotated[
    ListNotificationsUseCase, Depends(get_list_notifications_use_case)
]
