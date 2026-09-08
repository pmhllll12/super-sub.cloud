"""과금 명령·질의·결과."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class ViewCreditsQuery:
    user_id: UUID


@dataclass(frozen=True)
class CreditEntryResult:
    id: UUID
    delta: int
    reason: str
    created_at: datetime


@dataclass(frozen=True)
class CreditSummaryResult:
    balance: int
    history: list[CreditEntryResult] = field(default_factory=list)


@dataclass(frozen=True)
class AdjustCreditCommand:
    """수동 지급·조정. 🔴 **분석 경로에서 부르지 않는다** — 그 연결은 정어진이 붙인다."""

    actor_id: UUID
    target_user_id: UUID
    delta: int
    reason: str


@dataclass(frozen=True)
class ListCoachesQuery:
    page: int
    size: int


@dataclass(frozen=True)
class CoachResult:
    id: UUID
    name: str
    contact: str


@dataclass(frozen=True)
class CoachListResult:
    items: list[CoachResult]
    total: int
    page: int
    size: int


@dataclass(frozen=True)
class GetCoachQuery:
    coach_id: UUID


@dataclass(frozen=True)
class RequestCoachReferralCommand:
    actor_id: UUID
    coach_id: UUID
    fee: Decimal


@dataclass(frozen=True)
class CoachReferralResult:
    id: UUID
    coach_id: UUID
    fee: Decimal
    created_at: datetime
