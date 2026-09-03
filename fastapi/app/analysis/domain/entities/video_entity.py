"""업로드된 클립과 그 규격 검사 결과. 부록 D 도메인 ② (영상·분석)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ValidationEntity:
    """클립 1개의 규격 검사 결과.

    🔴 **통과한 것도 행을 남긴다.** 반려만 기록하면 "아직 검사 안 한 것"과
    "통과한 것"이 구별되지 않는다 — SFR-001 이 요구하는 것은 검수 기준을
    나중에 확인할 수 있게 하는 것이라, 판정이 없는 상태와 통과가 같아 보이면
    안 된다.
    """

    passed: bool
    reject_reason: str | None
    checked_at: datetime


@dataclass(frozen=True)
class VideoEntity:
    """업로드된 클립 1개.

    **파일 자체는 여기에 없다** — 객체 저장소의 키만 들고 있다(PER-002).

    `analysis_status` 는 `analysis_job` 에서 읽어 온 표시용이다. 반려된 클립은
    작업을 만들지 않으므로 None 이다. 같은 영상을 다시 분석하면 작업이 여러 건
    이 되는데, 화면(`/videos`)이 보여주는 것은 **가장 최근 것**이다.
    """

    id: UUID
    user_id: UUID
    sport_code: str
    storage_key: str
    duration_ms: int | None
    side: str | None
    created_at: datetime
    validation: ValidationEntity | None = None
    analysis_job_id: UUID | None = None
    analysis_status: str | None = None
