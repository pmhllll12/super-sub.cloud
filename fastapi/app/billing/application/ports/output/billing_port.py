"""과금 출력 포트.

🔴 **`user` 는 다른 컨텍스트의 테이블이다.** `user_exists` 구현이 `table()`/
`column()` 원시 쿼리로 필요한 컬럼만 읽는다(`review` 가 같은 이유로 하는 것과
같다) — 컨텍스트끼리 임포트하지 않는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.billing.domain.entities.billing_entity import (
    CoachEntity,
    CoachReferralEntity,
    CreditEntryEntity,
)


class BillingPort(ABC):
    @abstractmethod
    def credit_history(self, user_id: UUID) -> list[CreditEntryEntity]:
        """그 사용자의 증감 이력 전부. **시각순**으로 준다."""

    @abstractmethod
    def add_credit_entry(self, entry: CreditEntryEntity) -> None:
        """지급 또는 차감 한 행을 남긴다. 잔량 컬럼은 없다 — 조회 때 합산한다."""

    @abstractmethod
    def list_coaches(self, offset: int, limit: int) -> tuple[list[CoachEntity], int]:
        """(그 페이지의 코치, 전체 수)."""

    @abstractmethod
    def get_coach(self, coach_id: UUID) -> CoachEntity | None:
        """없으면 `None`."""

    @abstractmethod
    def save_referral(self, referral: CoachReferralEntity) -> None:
        """코치 연결 1행을 남긴다. **중복을 막지 않는다** — 같은 코치에 여러 번 연결을 요청할 수 있다."""

    @abstractmethod
    def user_exists(self, user_id: UUID) -> bool: ...
