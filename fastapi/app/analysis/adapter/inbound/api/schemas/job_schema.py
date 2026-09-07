"""워커 경로의 요청·응답 형태. 계약 3-8절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ClaimedJobResponse(BaseModel):
    """워커가 집은 작업 하나.

    🔴 **동작(루브릭)이 없다.** 담을 자리가 아직 없어서다(미결 `jin` 17번).
    `sport_code` 만으로는 축구·농구에서 루브릭이 둘로 갈리므로 **워커가 기본값으로
    돌리면 안 된다** — 갈리는 종목은 `failed` 로 보고한다.
    """

    job_id: UUID
    video_id: UUID
    storage_key: str
    sport_code: str
    side: str | None
    duration_ms: int | None


class FinishJobSchema(BaseModel):
    """완료 보고. `succeeded` 또는 `failed` 만 받는다.

    `finished_at` 을 받지 않는 것은 의도다 — 워커의 시계가 어긋나면 소요 시간이
    음수가 된다. 서버가 찍는다.
    """

    status: str = Field(min_length=1, max_length=20)
    failure_reason: str | None = Field(default=None, max_length=255)
