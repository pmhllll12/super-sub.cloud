"""평가·신뢰 명령·결과."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SubmitReviewCommand:
    actor_id: UUID
    match_id: UUID
    reviewee_id: UUID
    option_codes: list[str]


@dataclass(frozen=True)
class RecordNoShowCommand:
    actor_id: UUID
    match_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class FileReportCommand:
    actor_id: UUID
    target_user_id: UUID
    reason: str


@dataclass(frozen=True)
class ReviewOptionResult:
    code: str
    category: str
    label: str


@dataclass(frozen=True)
class ReviewResult:
    id: UUID
    match_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    submitted_at: datetime
    selected_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NoShowResult:
    id: UUID
    match_id: UUID
    user_id: UUID
    recorded_at: datetime


@dataclass(frozen=True)
class ReportResult:
    id: UUID
    target_user_id: UUID
    created_at: datetime
