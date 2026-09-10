"""리포트 적재 인터랙터. 미결 `jin` 27번.

완료 보고(`PATCH /internal/analysis-jobs/{id}`)가 `succeeded` + `report_key` 를
받으면 이 인터랙터가 그 키의 `report.json` 을 S3 에서 읽어 DB 로 옮긴다.

🔴 **트리거는 완료 보고 한 자리다** — 워커가 결과를 두 번 보내지 않게(계약 3-1
초안의 `metrics[]` inline POST 를 폐기한 이유). 이 인터랙터가 실패해도 작업은
성공한 것이므로, 부르는 쪽(`FinishJobInteractor`)이 예외를 삼키고 로그만 남긴다.
그때 리포트는 객체 저장소에 그대로 있고 나중에 다시 적재하면 된다.
"""

from __future__ import annotations

from uuid import UUID

from app.analysis.application.ports.input.report_ingest_use_case import (
    IngestReportUseCase,
)
from app.analysis.application.ports.output.report_ingest_port import ReportIngestPort
from app.analysis.application.ports.output.storage_port import StoragePort
from app.analysis.application.use_cases.report_parser import parse_report


class IngestReportInteractor(IngestReportUseCase):
    def __init__(
        self, storage: StoragePort | None, repository: ReportIngestPort
    ) -> None:
        self._storage = storage
        self._repository = repository

    def __call__(self, job_id: UUID, report_key: str) -> None:
        if self._storage is None:
            raise RuntimeError("객체 저장소가 설정되지 않아 리포트를 읽을 수 없습니다.")

        raw = self._storage.read_object(report_key)
        if raw is None:
            raise FileNotFoundError(f"리포트가 저장소에 없습니다: {report_key}")

        parsed = parse_report(raw)  # UnsupportedReportSchema / MalformedReport
        if not self._repository.replace_for_job(job_id, parsed):
            raise LookupError(f"적재할 작업이 없습니다: {job_id}")
