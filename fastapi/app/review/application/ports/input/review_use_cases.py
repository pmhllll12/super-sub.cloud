"""평가·신뢰 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.review.application.dtos.review_dto import (
    FileReportCommand,
    NoShowResult,
    RecordNoShowCommand,
    ReportResult,
    ReviewOptionResult,
    ReviewResult,
    SubmitReviewCommand,
)


class ListReviewOptionsUseCase(ABC):
    @abstractmethod
    def __call__(self) -> list[ReviewOptionResult]:
        """평가 화면이 보여줄 선택지. **노출 순서대로** 온다."""


class SubmitReviewUseCase(ABC):
    @abstractmethod
    def __call__(self, command: SubmitReviewCommand) -> ReviewResult:
        """경기가 끝난 뒤 확정된 참가자끼리 평가한다."""


class RecordNoShowUseCase(ABC):
    @abstractmethod
    def __call__(self, command: RecordNoShowCommand) -> NoShowResult:
        """불참을 기록한다. **주최 팀 주장만.**"""


class FileReportUseCase(ABC):
    @abstractmethod
    def __call__(self, command: FileReportCommand) -> ReportResult:
        """신고를 접수한다."""
