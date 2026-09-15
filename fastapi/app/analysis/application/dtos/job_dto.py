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
    # `detect` 작업의 결과 (미결 `ho` 44번). `succeeded`+`detect`일 때만 뜻이
    # 있다 — `report_key`처럼 여기서 종류를 안 가린다(리포트 적재는 `report_key`
    # 유무로 이미 갈린다, `analyze` 워커는 이 필드를 안 보낸다).
    detection_result: dict | None = None


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
    # `"analyze"` | `"detect"` (미결 `ho` 44번).
    job_type: str = "analyze"


@dataclass(frozen=True)
class RequestDetectionCommand:
    """지금 이 영상에서 잡힌 사람들을 검출해 달라는 요청 (미결 `ho` 44번)."""

    user_id: UUID
    video_id: UUID
    # 검출할 시각(ms). 안 주면 기본값 — `worker-interface.md`의 `at_ms`
    # 예시(1000ms)를 그대로 따른다. `agent`의 `anchor_frame_for`가 실제
    # 프레임으로 바꾼다 — 여기서는 값만 나른다.
    at_ms: int = 1000


@dataclass(frozen=True)
class DetectionStatusQuery:
    user_id: UUID
    video_id: UUID


@dataclass(frozen=True)
class DetectionStatusResult:
    job_id: UUID
    status: str
    failure_reason: str | None
    detection_result: dict | None
