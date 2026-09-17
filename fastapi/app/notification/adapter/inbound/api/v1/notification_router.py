"""알림 라우터. 계약 문서 3-12절. 미결 `jin` 35번.

**폴링 방식이다.** 웹소켓·푸시 인프라가 아직 없어서, 이미 쓰는 "몇 초마다 GET"
패턴(분석 상태 확인)을 그대로 쓴다. 실시간이 필요해지면 이 위에 전달 채널만
얹으면 된다 — 저장 방식(이 테이블·엔드포인트)은 그대로다.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserId
from app.notification.adapter.inbound.api.schemas.notification_schema import (
    NotificationResponse,
)
from app.notification.application.dtos.notification_dto import (
    ListNotificationsQuery,
    MarkNotificationReadCommand,
)
from app.notification.dependencies.list_notifications_provider import (
    ListNotificationsUseCaseDep,
)
from app.notification.dependencies.mark_notification_read_provider import (
    MarkNotificationReadUseCaseDep,
)

notification_router = APIRouter(tags=["notifications"])


@notification_router.get(
    "/me/notifications", response_model=list[NotificationResponse]
)
def list_notifications(
    user_id: CurrentUserId,
    use_case: ListNotificationsUseCaseDep,
    unread_only: bool = False,
):
    """최신순, 최대 50건."""
    return use_case(
        ListNotificationsQuery(recipient_id=user_id, unread_only=unread_only)
    )


@notification_router.patch(
    "/me/notifications/{notification_id}/read", response_model=NotificationResponse
)
def mark_notification_read(
    notification_id: UUID,
    user_id: CurrentUserId,
    use_case: MarkNotificationReadUseCaseDep,
):
    """이미 읽었어도 200으로 그대로 돌려준다(멱등). 404면 내 알림이 아니거나 없다."""
    return use_case(
        MarkNotificationReadCommand(actor_id=user_id, notification_id=notification_id)
    )
