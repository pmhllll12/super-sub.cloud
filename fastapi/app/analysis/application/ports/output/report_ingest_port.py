"""출력 포트 — 리포트 적재 저장. 미결 `jin` 27번.

포트를 두는 이유는 계약 테스트가 실제 DB 없이 돌게 하기 위해서다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.analysis.application.use_cases.report_parser import ParsedReport


class UnknownMetricCode(Exception):
    """`report.json` 이 `metric_definition` 에 없는 지표 코드를 담고 있다.

    시드가 빠졌거나 루브릭이 코드를 늘렸는데 새 마이그레이션이 안 나온 경우다.
    반쯤 적재하지 않고 통째로 거부한다(계약 3-1 `UNKNOWN_METRIC_CODE`).
    """


class ReportIngestPort(ABC):
    @abstractmethod
    def replace_for_job(self, job_id: UUID, parsed: ParsedReport) -> bool:
        """그 작업의 기존 적재(있으면)를 지우고 새로 넣는다.

        작업이 없으면 `False`. 넣었으면 `True`. 지표 코드가 정의에 없으면
        `UnknownMetricCode`.
        """
