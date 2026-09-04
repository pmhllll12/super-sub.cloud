"""평가·신뢰 엔티티. 부록 D 도메인 ⑤."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ReviewOptionEntity:
    """평가 선택지 하나. 화면이 `category` 로 묶고 `sort_order` 로 줄 세운다."""

    code: str
    category: str
    label: str
    sort_order: int


@dataclass(frozen=True)
class ReviewEntity:
    """평가 1건.

    🔴 **점수가 없다.** 고른 것이 `selected_codes` 로 남을 뿐이고, 신뢰도는
    이것을 집계해서 나중에 계산한다(D.4). 여기에 총점을 두면 선택형이 아니게 된다.
    """

    id: UUID
    match_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    submitted_at: datetime
    selected_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NoShowEntity:
    id: UUID
    match_id: UUID
    user_id: UUID
    recorded_at: datetime


@dataclass(frozen=True)
class ReportEntity:
    id: UUID
    reporter_id: UUID
    target_user_id: UUID
    reason: str
    created_at: datetime
