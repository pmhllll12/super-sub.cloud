"""알림 저장소 프로바이더. `user_repository_provider.py`와 같은 관례."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.notification.adapter.outbound.pg.notification_pg_repository import (
    NotificationPgRepository,
)
from app.notification.application.ports.output.notification_port import (
    NotificationPort,
)


def get_notification_repository(
    session: Annotated[Session, Depends(get_session)],
) -> NotificationPort:
    return NotificationPgRepository(session)


NotificationRepositoryDep = Annotated[
    NotificationPort, Depends(get_notification_repository)
]
