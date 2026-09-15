"""지인 신청·검색 HTTP 모델. 계약 문서 3-12절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339


class UserSearchItemResponse(BaseModel):
    id: UUID
    nickname: str


class RequestContactSchema(BaseModel):
    target_user_id: UUID
    note: str | None = Field(default=None, max_length=200)


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_user_id: UUID
    target_user_id: UUID
    note: str | None
    accepted_at: Rfc3339 | None
    created_at: Rfc3339


class ContactSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact_id: UUID
    user_id: UUID
    nickname: str
    # 내가 신청자일 때만 채워진다 — `UserContactSummary` 참고.
    note: str | None
    accepted_at: Rfc3339


class ContactListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ContactSummaryResponse]
