"""분석 작업 명령·결과."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class FinishJobCommand:
    job_id: UUID
    status: str
    failure_reason: str | None = None
    # 워커가 만든 리포트를 가리키는 버킷 상대 S3 키 (미결 `paik` 11번).
    # `succeeded` 일 때만 뜻이 있다 — 인터랙터가 그렇게 거른다.
    report_key: str | None = None


@dataclass(frozen=True)
class ClaimedJobResult:
    job_id: UUID
    video_id: UUID
    storage_key: str
    sport_code: str
    side: str | None
    duration_ms: int | None
    # 「이 사람으로 분석」 (미결 `paik` 6번). 없으면 둘 다 None.
    subject_box: list[float] | None = None
    subject_at_ms: int | None = None
    # 「집중해서 볼 항목」 (미결 `paik` 8번). 빈/None 이면 「전체」.
    focus: list[str] | None = None
