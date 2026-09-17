"""입력 포트 — 리포트 적재. 미결 `jin` 27번."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class IngestReportUseCase(ABC):
    @abstractmethod
    def __call__(self, job_id: UUID, report_key: str) -> None:
        """`report_key` 의 `report.json` 을 읽어 그 작업의 DB 적재를 채운다.

        재분석이면 앞의 적재를 덮는다. 스키마 버전이 낯설거나 파일이 없으면
        예외를 올린다 — 부르는 쪽(완료 보고)이 best-effort 로 삼킨다.
        """
