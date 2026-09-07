"""분석 작업 라우터 — **워커 전용**. 계약 3-8절.

미결 `ho` 17번(큐를 소비하는 것이 없다)에 대한 백엔드 쪽 골격이다. 워커가
**가져가는(pull)** 방식인 이유는 그 항목의 「답변」에 적어 두었다. 요약하면 GPU
인스턴스가 자동 종료되므로 밀어 주는(push) 방식은 대상이 꺼져 있을 때 실패하고,
루브릭을 고르려면 종목이 필요한데 그건 S3 가 아니라 DB 에 있다.

🔴 **경로가 `/internal/` 로 시작한다.** 사람 토큰으로는 들어올 수 없고
`X-Worker-Token` 헤더를 본다(`app/core/deps.py` 의 `require_worker`).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.analysis.adapter.inbound.api.schemas.job_schema import (
    ClaimedJobResponse,
    FinishJobSchema,
)
from app.analysis.application.dtos.job_dto import ClaimedJobResult, FinishJobCommand
from app.analysis.dependencies.job_providers import (
    ClaimJobUseCaseDep,
    FinishJobUseCaseDep,
)
from app.core.deps import WorkerAuth

job_router = APIRouter(tags=["worker"], dependencies=[WorkerAuth])


@job_router.post(
    "/internal/analysis-jobs/claim",
    response_model=ClaimedJobResponse | None,
    responses={204: {"description": "큐가 비었다"}},
)
def claim_job(use_case: ClaimJobUseCaseDep, response: Response) -> ClaimedJobResult | None:
    """큐에서 가장 오래된 작업 하나를 집어 `running` 으로 바꾼다.

    **큐가 비면 `204` 다 — 오류가 아니다.** 워커가 빈 큐를 오류로 읽으면 로그가
    빈 폴링으로 가득 찬다.

    `POST` 인 이유는 **상태를 바꾸기 때문**이다. 이름이 조회처럼 보여도 이 호출은
    작업을 하나 소비한다 — `GET` 으로 두면 프록시·클라이언트가 마음대로 재시도해서
    작업이 조용히 사라진다.
    """
    claimed = use_case()
    if claimed is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return claimed


@job_router.patch(
    "/internal/analysis-jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT
)
def finish_job(
    job_id: UUID, body: FinishJobSchema, use_case: FinishJobUseCaseDep
) -> None:
    """집었던 작업을 끝낸다. `succeeded` 또는 `failed` 만 받는다.

    | 에러 | 뜻 |
    |---|---|
    | 404 `JOB_NOT_FOUND` | 없는 작업이다 |
    | 409 `JOB_NOT_RUNNING` | 집지 않았거나 이미 끝났다. **재시도해도 소용없다** |
    | 422 `INVALID_JOB_STATUS` | `queued`·`running` 으로는 보고할 수 없다 |
    """
    use_case(
        FinishJobCommand(
            job_id=job_id, status=body.status, failure_reason=body.failure_reason
        )
    )
