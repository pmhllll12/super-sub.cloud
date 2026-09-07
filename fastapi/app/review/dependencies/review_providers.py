"""평가·신뢰 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.review.adapter.outbound.pg.review_pg_repository import ReviewPgRepository
from app.review.application.ports.input.review_use_cases import (
    FileReportUseCase,
    ListReviewOptionsUseCase,
    RecordNoShowUseCase,
    SubmitReviewUseCase,
)
from app.review.application.ports.output.review_port import ReviewPort
from app.review.application.use_cases.review_interactors import (
    FileReportInteractor,
    ListReviewOptionsInteractor,
    RecordNoShowInteractor,
    SubmitReviewInteractor,
)


def get_review_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ReviewPort:
    return ReviewPgRepository(session)


ReviewRepositoryDep = Annotated[ReviewPort, Depends(get_review_repository)]


def get_list_options_use_case(
    repository: ReviewRepositoryDep,
) -> ListReviewOptionsUseCase:
    return ListReviewOptionsInteractor(repository)


def get_submit_review_use_case(repository: ReviewRepositoryDep) -> SubmitReviewUseCase:
    return SubmitReviewInteractor(repository)


def get_record_no_show_use_case(repository: ReviewRepositoryDep) -> RecordNoShowUseCase:
    return RecordNoShowInteractor(repository)


def get_file_report_use_case(repository: ReviewRepositoryDep) -> FileReportUseCase:
    return FileReportInteractor(repository)


ListReviewOptionsUseCaseDep = Annotated[
    ListReviewOptionsUseCase, Depends(get_list_options_use_case)
]
SubmitReviewUseCaseDep = Annotated[
    SubmitReviewUseCase, Depends(get_submit_review_use_case)
]
RecordNoShowUseCaseDep = Annotated[
    RecordNoShowUseCase, Depends(get_record_no_show_use_case)
]
FileReportUseCaseDep = Annotated[FileReportUseCase, Depends(get_file_report_use_case)]
