"""알림 HTTP 모델. 계약 문서 3-12절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.shared import Rfc3339


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    actor_user_id: UUID | None
    subject_type: str | None
    subject_id: UUID | None
    read_at: Rfc3339 | None
    created_at: Rfc3339
