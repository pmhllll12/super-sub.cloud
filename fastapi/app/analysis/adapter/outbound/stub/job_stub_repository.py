"""메모리 큐. 계약 테스트가 DB 없이 돌기 위한 것이다.

⚠️ **동시성은 여기서 검증되지 않는다.** `SKIP LOCKED` 와 한 문장 집기가 실제로
두 워커를 갈라 주는지는 진짜 PostgreSQL 이라야 확인된다 —
`tests/analysis/adapter/test_job_db.py` 가 그 자리다. 여기서는 상태 전이와
응답 형태만 본다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.domain.entities.job_entity import ClaimedJobEntity
from app.analysis.domain.rules.job_rules import QUEUED, RUNNING


@dataclass
class _Row:
    job_id: UUID
    video_id: UUID
    storage_key: str
    sport_code: str
    side: str | None
    duration_ms: int | None
    created_at: datetime
    status: str = QUEUED
    failure_reason: str | None = None


_JOBS: dict[UUID, _Row] = {}


def reset_jobs() -> None:
    _JOBS.clear()


def enqueue(
    job_id: UUID,
    video_id: UUID,
    *,
    storage_key: str = "videos/stub/clip.mp4",
    sport_code: str = "baseball",
    side: str | None = None,
    duration_ms: int | None = 5_000,
    created_at: datetime | None = None,
) -> None:
    """검사가 "이런 작업이 큐에 있다"고 알려 준다."""
    _JOBS[job_id] = _Row(
        job_id=job_id,
        video_id=video_id,
        storage_key=storage_key,
        sport_code=sport_code,
        side=side,
        duration_ms=duration_ms,
        created_at=created_at or datetime.now(timezone.utc),
    )


def status_of(job_id: UUID) -> str | None:
    row = _JOBS.get(job_id)
    return row.status if row else None


def failure_reason_of(job_id: UUID) -> str | None:
    row = _JOBS.get(job_id)
    return row.failure_reason if row else None


class StubJobRepository(JobPort):
    def claim_next(self) -> ClaimedJobEntity | None:
        waiting = [r for r in _JOBS.values() if r.status == QUEUED]
        if not waiting:
            return None
        row = min(waiting, key=lambda r: r.created_at)   # 오래된 것부터
        row.status = RUNNING
        return ClaimedJobEntity(
            job_id=row.job_id,
            video_id=row.video_id,
            storage_key=row.storage_key,
            sport_code=row.sport_code,
            side=row.side,
            duration_ms=row.duration_ms,
        )

    def finish(
        self, job_id: UUID, status: str, failure_reason: str | None
    ) -> str | None:
        row = _JOBS.get(job_id)
        if row is None:
            return "missing"
        if row.status != RUNNING:
            return row.status
        row.status = status
        row.failure_reason = failure_reason
        return None
