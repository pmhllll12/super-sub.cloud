"""지인 신청·검색 HTTP 모델. 계약 문서 3-12절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339


class UserSearchItemResponse(BaseModel):
    id: UUID
    nickname: str
    # 그 사람의 공개 카드로 가는 값 — 카드를 안 만들었으면 `null`.
    # 🔴 내부 `user_id` 로 카드를 찾게 하지 않는다(미결 `paik` 39번).
    card_public_slug: str | None = None


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
    # 공개 카드 슬러그 — 카드를 안 만들었으면 `null`(미결 `paik` 39번).
    card_public_slug: str | None = None


class ContactListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ContactSummaryResponse]
