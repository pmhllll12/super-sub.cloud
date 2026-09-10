"""분석 작업 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.pg.job_pg_repository import JobPgRepository
from app.analysis.adapter.outbound.pg.report_ingest_pg_repository import (
    ReportIngestPgRepository,
)
from app.analysis.application.ports.input.job_use_cases import (
    ClaimJobUseCase,
    FinishJobUseCase,
)
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.application.ports.output.report_ingest_port import ReportIngestPort
from app.analysis.application.use_cases.job_interactors import (
    ClaimJobInteractor,
    FinishJobInteractor,
)
from app.analysis.application.use_cases.report_ingest_interactor import (
    IngestReportInteractor,
)
from app.analysis.dependencies.video_providers import (
    StorageOptionalDep,
    VideoRepositoryDep,
)
from app.core.config import settings
from app.core.database import get_session


def get_job_repository(
    session: Annotated[Session, Depends(get_session)],
) -> JobPort:
    return JobPgRepository(session)


JobRepositoryDep = Annotated[JobPort, Depends(get_job_repository)]


def get_claim_job_use_case(
    repository: JobRepositoryDep,
    video_repository: VideoRepositoryDep,
    storage: StorageOptionalDep,
) -> ClaimJobUseCase:
    return ClaimJobInteractor(
        repository,
        settings.analysis_job_timeout_minutes,
        video_repository=video_repository,
        storage=storage,
        provisional_ttl_hours=settings.provisional_video_ttl_hours,
    )


def get_report_ingest_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ReportIngestPort:
    return ReportIngestPgRepository(session)


ReportIngestRepositoryDep = Annotated[
    ReportIngestPort, Depends(get_report_ingest_repository)
]


def get_finish_job_use_case(
    repository: JobRepositoryDep,
    ingest_repository: ReportIngestRepositoryDep,
    storage: StorageOptionalDep,
) -> FinishJobUseCase:
    # 적재는 완료 보고에 얹혀 돈다(미결 `jin` 27번). `repository.finish` 가 상태를
    # 먼저 커밋하므로 적재는 그 뒤에 같은 세션에서 돈다 — 적재가 실패하면
    # `FinishJobInteractor` 가 삼키고, 세션은 요청 끝에 롤백된다(커밋된 상태는
    # 남는다). 저장소가 없으면(로컬) 적재 인터랙터가 호출 시 실패하고 그것도 삼켜진다.
    ingest = IngestReportInteractor(storage, ingest_repository)
    return FinishJobInteractor(repository, ingest)


ClaimJobUseCaseDep = Annotated[ClaimJobUseCase, Depends(get_claim_job_use_case)]
FinishJobUseCaseDep = Annotated[FinishJobUseCase, Depends(get_finish_job_use_case)]
