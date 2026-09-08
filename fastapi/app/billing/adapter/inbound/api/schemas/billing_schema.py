"""과금 요청·응답 형태. 계약 3-10절."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.shared import Rfc3339


class CreditEntryResponse(BaseModel):
    id: UUID
    delta: int
    reason: str
    created_at: Rfc3339


class CreditSummaryResponse(BaseModel):
    """`balance` 는 `history` 의 `delta` 합이다 — 별도로 저장하지 않는다."""

    balance: int
    history: list[CreditEntryResponse]


class AdjustCreditSchema(BaseModel):
    """관리자의 수동 지급·조정. `reason` 값 목록은 아직 정해지지 않아 자유 텍스트다."""

    user_id: UUID
    delta: int
    reason: str = Field(min_length=1, max_length=200)


class CoachResponse(BaseModel):
    id: UUID
    name: str
    contact: str


class CoachListResponse(BaseModel):
    items: list[CoachResponse]
    total: int
    page: int
    size: int


class RequestCoachReferralSchema(BaseModel):
    fee: Decimal = Field(ge=0)


class CoachReferralResponse(BaseModel):
    id: UUID
    coach_id: UUID
    fee: Decimal
    created_at: Rfc3339
