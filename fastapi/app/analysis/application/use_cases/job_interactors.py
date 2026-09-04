"""분석 작업 인터랙터. 판단은 `domain/rules/job_rules.py` 가 한다."""

from __future__ import annotations

import logging

from app.analysis.application.dtos.job_dto import ClaimedJobResult, FinishJobCommand
from app.analysis.application.ports.input.job_use_cases import (
    ClaimJobUseCase,
    FinishJobUseCase,
)
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.domain.rules.job_rules import is_terminal
from app.core.errors import ApiError

# 회수는 **조용히 일어나면 안 된다.** 작업이 되돌려졌다는 것은 워커나 인스턴스에
# 무슨 일이 있었다는 뜻이라, 나중에 "왜 두 번 분석됐나"를 되짚을 자리가 필요하다.
logger = logging.getLogger("supersub.analysis")


class ClaimJobInteractor(ClaimJobUseCase):
    def __init__(self, repository: JobPort, timeout_minutes: int) -> None:
        self._repository = repository
        self._timeout_minutes = timeout_minutes

    def __call__(self) -> ClaimedJobResult | None:
        # 🔴 집기 **전에** 멈춘 것을 회수한다. 별도 스케줄러를 두지 않는 이유는
        #    워커가 주기적으로 이 경로를 부르기 때문이다 — 회수가 필요한 시점은
        #    정확히 "누군가 일을 달라고 할 때"고, 그때마다 돈다. 타이머·크론을
        #    새로 만들면 그것이 죽었는지 또 확인해야 한다.
        requeued, failed = self._repository.reclaim_stale(self._timeout_minutes)
        if requeued or failed:
            logger.warning(
                "멈춘 분석 작업을 회수했다: 큐로 %d 건, 실패로 %d 건", requeued, failed
            )

        job = self._repository.claim_next()
        if job is None:
            return None
        return ClaimedJobResult(
            job_id=job.job_id,
            video_id=job.video_id,
            storage_key=job.storage_key,
            sport_code=job.sport_code,
            side=job.side,
            duration_ms=job.duration_ms,
        )


class FinishJobInteractor(FinishJobUseCase):
    def __init__(self, repository: JobPort) -> None:
        self._repository = repository

    def __call__(self, command: FinishJobCommand) -> None:
        if not is_terminal(command.status):
            # `queued`·`running` 으로 되돌리는 것은 보고가 아니다. 열어 두면
            # 워커가 작업을 큐로 되던질 수 있게 되는데, 그건 재시도 정책이지
            # 완료 보고가 아니라 따로 정해야 한다.
            raise ApiError(
                422, "INVALID_JOB_STATUS", "끝난 상태만 보고할 수 있습니다."
            )

        blocked = self._repository.finish(
            command.job_id, command.status, command.failure_reason
        )
        if blocked is None:
            return
        if blocked == "missing":
            raise ApiError(404, "JOB_NOT_FOUND", "작업을 찾을 수 없습니다.")
        # 🔴 집지 않은 작업(`queued`)이나 이미 끝난 작업이다. 조용히 통과시키면
        #    두 번째 보고가 `finished_at` 을 뒤로 밀어 소요 시간이 늘어난다.
        raise ApiError(
            409, "JOB_NOT_RUNNING", f"진행 중인 작업이 아닙니다(현재 {blocked})."
        )
