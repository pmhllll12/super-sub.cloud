"""과금 엔티티. 부록 D 도메인 ⑥."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CreditEntryEntity:
    """크레딧 증감 1건.

    🔴 **잔량 컬럼이 없다.** 지급은 양수, 차감은 음수 한 행이고 잔량은
    `SUM(delta)`로 구한다(부록 D — 「크레딧 잔량은 delta의 누적합이다」).
    """

    id: UUID
    user_id: UUID
    delta: int
    reason: str
    created_at: datetime


@dataclass(frozen=True)
class CoachEntity:
    """제휴 코치 1명.

    🔴 **`user_id`가 없다.** 코치는 플랫폼 사용자가 아니라 외부 제휴자다.
    """

    id: UUID
    name: str
    contact: str


@dataclass(frozen=True)
class CoachReferralEntity:
    """코치 연결 1건."""

    id: UUID
    user_id: UUID
    coach_id: UUID
    fee: Decimal
    created_at: datetime
