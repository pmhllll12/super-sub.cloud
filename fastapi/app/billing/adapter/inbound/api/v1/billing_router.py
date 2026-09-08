"""과금 라우터. 계약 3-10절.

부록 D 도메인 ⑥ 을 여는 자리다(패킷 A, `docs/backend-work-split.md`). 「정해야
할 것」(무료 크레딧 지급 시점·액수, 분석 1건당 차감액, `reason` 값 목록)은
아직 정하지 않았다 — 이번 범위는 조회·지급(수동)·수동 조정까지다.

🔴 **크레딧 차감이 분석 경로(`POST /videos`)에 이어지지 않는다.** 컨텍스트
경계를 넘는 연결이라 정어진이 붙인다.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAdminUserId, CurrentUserId
from app.billing.adapter.inbound.api.schemas.billing_schema import (
    AdjustCreditSchema,
    CoachListResponse,
    CoachReferralResponse,
    CoachResponse,
    CreditSummaryResponse,
    RequestCoachReferralSchema,
)
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
from app.billing.dependencies.billing_providers import (
    AdjustCreditUseCaseDep,
    GetCoachUseCaseDep,
    ListCoachesUseCaseDep,
    RequestCoachReferralUseCaseDep,
    ViewCreditsUseCaseDep,
)

billing_router = APIRouter(tags=["billing"])


@billing_router.get("/credits", response_model=CreditSummaryResponse)
def view_credits(
    user_id: CurrentUserId, use_case: ViewCreditsUseCaseDep
) -> CreditSummaryResult:
    """내 크레딧 잔량과 이력. `/credits` 화면.

    **`balance` 는 컬럼이 아니라 `history` 의 `delta` 합이다** — 부록 D 가
    잔량을 파생값으로 정했다(D.4).
    """
    return use_case(ViewCreditsQuery(user_id=user_id))


@billing_router.post(
    "/admin/credits/adjustments",
    response_model=CreditSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def adjust_credit(
    body: AdjustCreditSchema,
    admin_id: CurrentAdminUserId,
    use_case: AdjustCreditUseCaseDep,
) -> CreditSummaryResult:
    """관리자의 수동 지급·조정. **양수는 지급, 음수는 차감**이다.

    | 에러 | 뜻 |
    |---|---|
    | 404 `USER_NOT_FOUND` | 대상 사용자가 없다 |
    | 422 `INVALID_DELTA` | 증감액이 0이다 |
    """
    return use_case(
        AdjustCreditCommand(
            actor_id=admin_id,
            target_user_id=body.user_id,
            delta=body.delta,
            reason=body.reason,
        )
    )


@billing_router.get("/coaches", response_model=CoachListResponse)
def list_coaches(
    _user_id: CurrentUserId,
    use_case: ListCoachesUseCaseDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> CoachListResult:
    """`market/coaches` 목록 화면.

    ⚠️ 종목·가격·소개 문장 같은 값은 없다 — 부록 D 의 `coach`는 `id`·`name`·
    `contact` 셋뿐이다.
    """
    return use_case(ListCoachesQuery(page=page, size=size))


@billing_router.get("/coaches/{coach_id}", response_model=CoachResponse)
def get_coach(coach_id: UUID, _user_id: CurrentUserId, use_case: GetCoachUseCaseDep) -> CoachResult:
    """코치 상세. 404 `COACH_NOT_FOUND`."""
    return use_case(GetCoachQuery(coach_id=coach_id))


@billing_router.post(
    "/coaches/{coach_id}/referrals",
    response_model=CoachReferralResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_coach_referral(
    coach_id: UUID,
    body: RequestCoachReferralSchema,
    user_id: CurrentUserId,
    use_case: RequestCoachReferralUseCaseDep,
) -> CoachReferralResult:
    """코치 연결을 요청하면 기록한다. **중복을 막지 않는다.**

    | 에러 | 뜻 |
    |---|---|
    | 404 `COACH_NOT_FOUND` | 없는 코치 |
    | 422 `INVALID_FEE` | 수수료가 음수다 |
    """
    return use_case(
        RequestCoachReferralCommand(actor_id=user_id, coach_id=coach_id, fee=body.fee)
    )
