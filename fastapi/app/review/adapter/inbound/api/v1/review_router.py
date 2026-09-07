"""평가·신뢰 라우터. 계약 3-9절. SFR-008.

부록 D 도메인 ⑤ 를 여는 자리다. 스키마는 박민호가 09-03 에 냈고(`2649dd9`),
응용 계층은 정어진이 09-04 에 썼다 — 그 사이 「정해야 할 것」 셋을 정했고 근거는
`domain/rules/review_rules.py` 에 있다.

🔴 **평가에 점수가 없다.** 선택지를 고르는 형태다(3.4) — 총점을 두면 나쁜 평가
하나가 줄 수 있는 피해에 상한이 없어진다.
🔴 **신고·불참은 평가와 이어지지 않는다**(3.5). 제재는 별도 기록이다.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId
from app.review.adapter.inbound.api.schemas.review_schema import (
    FileReportSchema,
    NoShowResponse,
    RecordNoShowSchema,
    ReportResponse,
    ReviewOptionResponse,
    ReviewResponse,
    SubmitReviewSchema,
)
from app.review.application.dtos.review_dto import (
    FileReportCommand,
    NoShowResult,
    RecordNoShowCommand,
    ReportResult,
    ReviewOptionResult,
    ReviewResult,
    SubmitReviewCommand,
)
from app.review.dependencies.review_providers import (
    FileReportUseCaseDep,
    ListReviewOptionsUseCaseDep,
    RecordNoShowUseCaseDep,
    SubmitReviewUseCaseDep,
)

review_router = APIRouter(tags=["reviews"])


@review_router.get("/review-options", response_model=list[ReviewOptionResponse])
def list_review_options(
    user_id: CurrentUserId, use_case: ListReviewOptionsUseCaseDep
) -> list[ReviewOptionResult]:
    """평가 화면이 보여줄 선택지 전부.

    **배열의 순서가 화면 노출 순서다**(매너 · 실력 · 재매칭 · 주의).
    `category` 로 묶어 그리되 **순서는 서버가 준 것을 그대로** 쓰십시오 —
    카테고리를 알파벳순으로 정렬하면 「주의」가 맨 앞에 옵니다.
    """
    return use_case()


@review_router.post(
    "/matches/{match_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_review(
    match_id: UUID,
    body: SubmitReviewSchema,
    user_id: CurrentUserId,
    use_case: SubmitReviewUseCaseDep,
) -> ReviewResult:
    """경기가 끝난 뒤 **확정된 참가자끼리** 평가한다.

    | 에러 | 뜻 |
    |---|---|
    | 403 `FORBIDDEN` | 내가 이 경기의 확정 참가자가 아니다 |
    | 404 `MATCH_NOT_FOUND` | 없는 경기 |
    | 409 `ALREADY_REVIEWED` | 이미 평가한 상대 (경기당 1회 — DB 제약) |
    | 422 `MATCH_NOT_PLAYED` | 아직 안 끝난 경기 |
    | 422 `REVIEW_WINDOW_CLOSED` | **경기 후 14일**이 지났다 |
    | 422 `SELF_REVIEW` · `NOT_A_PARTICIPANT` · `UNKNOWN_OPTION` | 각각 자기 평가 · 대상이 참가자 아님 · 없는 선택지 |
    """
    return use_case(
        SubmitReviewCommand(
            actor_id=user_id,
            match_id=match_id,
            reviewee_id=body.reviewee_id,
            option_codes=body.option_codes,
        )
    )


@review_router.post(
    "/matches/{match_id}/no-shows",
    response_model=NoShowResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_no_show(
    match_id: UUID,
    body: RecordNoShowSchema,
    user_id: CurrentUserId,
    use_case: RecordNoShowUseCaseDep,
) -> NoShowResult:
    """불참을 기록한다. 🔴 **주최 팀 주장만.**

    제재 기록이라 만들 수 있는 사람을 좁혔다 — 참가자 누구나 붙일 수 있으면
    사이가 틀어진 상대에게 서로 붙일 수 있고, **스키마에 기록자 컬럼이 없어**
    나중에 누가 붙였는지도 못 따진다.

    | 에러 | 뜻 |
    |---|---|
    | 403 `FORBIDDEN` | 주장이 아니다 |
    | 409 `ALREADY_RECORDED` | 경기당 1인 1건 (DB 제약) |
    | 422 `MATCH_NOT_PLAYED` · `NOT_A_PARTICIPANT` | 아직 안 끝남 · 확정자가 아님 |
    """
    return use_case(
        RecordNoShowCommand(actor_id=user_id, match_id=match_id, user_id=body.user_id)
    )


@review_router.post(
    "/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED
)
def file_report(
    body: FileReportSchema, user_id: CurrentUserId, use_case: FileReportUseCaseDep
) -> ReportResult:
    """신고를 접수한다.

    ⚠️ **접수만 한다. 처리하는 경로는 없다** — 관리자 화면이 생기면 붙인다.
    같은 사람을 여러 번 신고할 수 있다(중복을 막지 않는다).
    """
    return use_case(
        FileReportCommand(
            actor_id=user_id, target_user_id=body.target_user_id, reason=body.reason
        )
    )
