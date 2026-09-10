"""읽기 경로가 화면에 내보내는 리포트 모양. 미결 `jin` 27번 · `paik` 7번.

🔴 **허용목록이다.** 계약 3-1 이 "DB 조립"을 택한 이유가 이것 — DB 에 있는 것을
전부 흘리지 않고 여기 적힌 필드만 나간다. 수치(총점·항목별 등급·`stat`)는 카드
경로가 따로 읽으므로 여기 없고, `band` 는 임계값이 검수 전이라 선수에게 내지
않는다(미결 24번).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ReadReportQuery:
    video_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class ReportCriterionView:
    criterion_id: str
    name: str
    grade: int | None       # None = 제외(skipped). 0 점이 아니다.
    title: str | None
    evidence: str | None
    metric_ref: str | None
    skipped: bool


@dataclass(frozen=True)
class ReportSceneView:
    """판단의 근거가 된 장면. 시각은 수치가 아니라 찾아가는 자리다."""

    metric_code: str
    label: str
    at_seconds: float


@dataclass(frozen=True)
class ReportView:
    video_id: UUID
    analyzed_at: datetime
    summary: str
    provisional: bool | None
    breakdown: list[ReportCriterionView]
    scenes: list[ReportSceneView]
    previews: dict[str, Any] | None
    keypoint_quality: dict[str, Any] | None
