"""과금 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.billing.adapter.outbound.pg.billing_pg_repository import BillingPgRepository
from app.billing.application.ports.input.billing_use_cases import (
    AdjustCreditUseCase,
    GetCoachUseCase,
    ListCoachesUseCase,
    RequestCoachReferralUseCase,
    ViewCreditsUseCase,
)
from app.billing.application.ports.output.billing_port import BillingPort
from app.billing.application.use_cases.billing_interactors import (
    AdjustCreditInteractor,
    GetCoachInteractor,
    ListCoachesInteractor,
    RequestCoachReferralInteractor,
    ViewCreditsInteractor,
)
from app.core.database import get_session


def get_billing_repository(
    session: Annotated[Session, Depends(get_session)],
) -> BillingPort:
    return BillingPgRepository(session)


BillingRepositoryDep = Annotated[BillingPort, Depends(get_billing_repository)]


def get_view_credits_use_case(repository: BillingRepositoryDep) -> ViewCreditsUseCase:
    return ViewCreditsInteractor(repository)


def get_adjust_credit_use_case(
    repository: BillingRepositoryDep,
) -> AdjustCreditUseCase:
    return AdjustCreditInteractor(repository)


def get_list_coaches_use_case(repository: BillingRepositoryDep) -> ListCoachesUseCase:
    return ListCoachesInteractor(repository)


def get_get_coach_use_case(repository: BillingRepositoryDep) -> GetCoachUseCase:
    return GetCoachInteractor(repository)


def get_request_coach_referral_use_case(
    repository: BillingRepositoryDep,
) -> RequestCoachReferralUseCase:
    return RequestCoachReferralInteractor(repository)


ViewCreditsUseCaseDep = Annotated[
    ViewCreditsUseCase, Depends(get_view_credits_use_case)
]
AdjustCreditUseCaseDep = Annotated[
    AdjustCreditUseCase, Depends(get_adjust_credit_use_case)
]
ListCoachesUseCaseDep = Annotated[
    ListCoachesUseCase, Depends(get_list_coaches_use_case)
]
GetCoachUseCaseDep = Annotated[GetCoachUseCase, Depends(get_get_coach_use_case)]
RequestCoachReferralUseCaseDep = Annotated[
    RequestCoachReferralUseCase, Depends(get_request_coach_referral_use_case)
]
