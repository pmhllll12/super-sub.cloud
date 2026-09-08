"""과금 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.billing.application.dtos.billing_dto import (
    AdjustCreditCommand,
    CoachListResult,
    CoachReferralResult,
    CoachResult,
    CreditSummaryResult,
    GetCoachQuery,
    ListCoachesQuery,
    RequestCoachReferralCommand,
    ViewCreditsQuery,
)


class ViewCreditsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ViewCreditsQuery) -> CreditSummaryResult:
        """내 크레딧 잔량과 이력. `/credits` 화면."""


class AdjustCreditUseCase(ABC):
    @abstractmethod
    def __call__(self, command: AdjustCreditCommand) -> CreditSummaryResult:
        """수동 지급·조정 — **관리자 전용.** 대상 사용자의 새 잔량·이력을 돌려준다."""


class ListCoachesUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListCoachesQuery) -> CoachListResult:
        """`market/coaches` 목록 화면."""


class GetCoachUseCase(ABC):
    @abstractmethod
    def __call__(self, query: GetCoachQuery) -> CoachResult:
        """코치 상세."""


class RequestCoachReferralUseCase(ABC):
    @abstractmethod
    def __call__(self, command: RequestCoachReferralCommand) -> CoachReferralResult:
        """코치 연결을 요청하면 기록한다."""
