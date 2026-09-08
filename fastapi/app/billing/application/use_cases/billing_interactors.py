"""과금 인터랙터. 판단은 `domain/rules/billing_rules.py` 가 한다."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.billing.application.dtos.billing_dto import (
    AdjustCreditCommand,
    CoachListResult,
    CoachReferralResult,
    CoachResult,
    CreditEntryResult,
    CreditSummaryResult,
    GetCoachQuery,
    ListCoachesQuery,
    RequestCoachReferralCommand,
    ViewCreditsQuery,
)
from app.billing.application.ports.input.billing_use_cases import (
    AdjustCreditUseCase,
    GetCoachUseCase,
    ListCoachesUseCase,
    RequestCoachReferralUseCase,
    ViewCreditsUseCase,
)
from app.billing.application.ports.output.billing_port import BillingPort
from app.billing.domain.entities.billing_entity import (
    CoachReferralEntity,
    CreditEntryEntity,
)
from app.billing.domain.rules.billing_rules import is_valid_delta, is_valid_fee
from app.core.errors import ApiError


def _summary(repository: BillingPort, user_id) -> CreditSummaryResult:
    history = repository.credit_history(user_id)
    return CreditSummaryResult(
        balance=sum(e.delta for e in history),
        history=[
            CreditEntryResult(
                id=e.id, delta=e.delta, reason=e.reason, created_at=e.created_at
            )
            for e in history
        ],
    )


class ViewCreditsInteractor(ViewCreditsUseCase):
    def __init__(self, repository: BillingPort) -> None:
        self._repository = repository

    def __call__(self, query: ViewCreditsQuery) -> CreditSummaryResult:
        return _summary(self._repository, query.user_id)


class AdjustCreditInteractor(AdjustCreditUseCase):
    def __init__(self, repository: BillingPort) -> None:
        self._repository = repository

    def __call__(self, command: AdjustCreditCommand) -> CreditSummaryResult:
        if not is_valid_delta(command.delta):
            raise ApiError(422, "INVALID_DELTA", "증감액은 0일 수 없습니다.")
        if not self._repository.user_exists(command.target_user_id):
            raise ApiError(404, "USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")

        self._repository.add_credit_entry(
            CreditEntryEntity(
                id=uuid4(),
                user_id=command.target_user_id,
                delta=command.delta,
                reason=command.reason,
                created_at=datetime.now(timezone.utc),
            )
        )
        return _summary(self._repository, command.target_user_id)


class ListCoachesInteractor(ListCoachesUseCase):
    def __init__(self, repository: BillingPort) -> None:
        self._repository = repository

    def __call__(self, query: ListCoachesQuery) -> CoachListResult:
        offset = (query.page - 1) * query.size
        coaches, total = self._repository.list_coaches(offset=offset, limit=query.size)
        return CoachListResult(
            items=[
                CoachResult(id=c.id, name=c.name, contact=c.contact) for c in coaches
            ],
            total=total,
            page=query.page,
            size=query.size,
        )


class GetCoachInteractor(GetCoachUseCase):
    def __init__(self, repository: BillingPort) -> None:
        self._repository = repository

    def __call__(self, query: GetCoachQuery) -> CoachResult:
        coach = self._repository.get_coach(query.coach_id)
        if coach is None:
            raise ApiError(404, "COACH_NOT_FOUND", "코치를 찾을 수 없습니다.")
        return CoachResult(id=coach.id, name=coach.name, contact=coach.contact)


class RequestCoachReferralInteractor(RequestCoachReferralUseCase):
    def __init__(self, repository: BillingPort) -> None:
        self._repository = repository

    def __call__(self, command: RequestCoachReferralCommand) -> CoachReferralResult:
        if self._repository.get_coach(command.coach_id) is None:
            raise ApiError(404, "COACH_NOT_FOUND", "코치를 찾을 수 없습니다.")
        if not is_valid_fee(command.fee):
            raise ApiError(422, "INVALID_FEE", "수수료는 0 이상이어야 합니다.")

        referral = CoachReferralEntity(
            id=uuid4(),
            user_id=command.actor_id,
            coach_id=command.coach_id,
            fee=command.fee,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_referral(referral)
        return CoachReferralResult(
            id=referral.id,
            coach_id=referral.coach_id,
            fee=referral.fee,
            created_at=referral.created_at,
        )
