"""분석 작업 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.pg.job_pg_repository import JobPgRepository
from app.analysis.application.ports.input.job_use_cases import (
    ClaimJobUseCase,
    FinishJobUseCase,
)
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.application.use_cases.job_interactors import (
    ClaimJobInteractor,
    FinishJobInteractor,
)
from app.core.config import settings
from app.core.database import get_session


def get_job_repository(
    session: Annotated[Session, Depends(get_session)],
) -> JobPort:
    return JobPgRepository(session)


JobRepositoryDep = Annotated[JobPort, Depends(get_job_repository)]


def get_claim_job_use_case(repository: JobRepositoryDep) -> ClaimJobUseCase:
    return ClaimJobInteractor(repository, settings.analysis_job_timeout_minutes)


def get_finish_job_use_case(repository: JobRepositoryDep) -> FinishJobUseCase:
    return FinishJobInteractor(repository)


ClaimJobUseCaseDep = Annotated[ClaimJobUseCase, Depends(get_claim_job_use_case)]
FinishJobUseCaseDep = Annotated[FinishJobUseCase, Depends(get_finish_job_use_case)]
