"""입력 포트 — 리포트 조회. 미결 `jin` 27번 · `paik` 7번."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.application.dtos.report_view_dto import ReadReportQuery, ReportView


class ReadReportUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ReadReportQuery) -> ReportView:
        """그 영상의 적재된 리포트. 자기 영상이 아니거나 없으면 404
        `VIDEO_NOT_FOUND`, 있으나 아직 적재 안 됐으면 404 `REPORT_NOT_READY`.
        """
