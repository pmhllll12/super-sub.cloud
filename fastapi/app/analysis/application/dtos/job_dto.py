"""분석 작업 명령·결과."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class FinishJobCommand:
    job_id: UUID
    status: str
    failure_reason: str | None = None


@dataclass(frozen=True)
class ClaimedJobResult:
    job_id: UUID
    video_id: UUID
    storage_key: str
    sport_code: str
    side: str | None
    duration_ms: int | None
