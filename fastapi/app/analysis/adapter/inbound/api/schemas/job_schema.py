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
    # 「이 사람으로 분석」 대상 (미결 `paik` 6번). 정규화 `[x, y, w, h]`(0~1)와
    # 그 박스를 그린 시각(ms). 🔴 **없으면 둘 다 `null` 이고 그게 정상**이다 —
    # 워커는 「자동으로 고르기」로 돈다. 있으면 `--subject-box x,y,w,h
    # --subject-at-ms` 로 넘긴다.
    subject_box: list[float] | None = None
    subject_at_ms: int | None = None
    # 「집중해서 볼 항목」 (미결 `paik` 8번). 루브릭 criteria id 리스트.
    # 🔴 **없거나 빈 리스트면 「전체적으로」**다 — 워커는 `--focus` 를 안 붙인다.
    # 있으면 `--focus a,b,c` 로 넘긴다.
    focus: list[str] | None = None


class FinishJobSchema(BaseModel):
    """완료 보고. `succeeded` 또는 `failed` 만 받는다.

    `finished_at` 을 받지 않는 것은 의도다 — 워커의 시계가 어긋나면 소요 시간이
    음수가 된다. 서버가 찍는다.
    """

    status: str = Field(min_length=1, max_length=20)
    failure_reason: str | None = Field(default=None, max_length=255)
    # 워커가 만든 리포트 하나를 가리키는 **버킷 상대 S3 키** (미결 `paik` 11번).
    # 예: `reports/<user_id>/<video_id>/report.json`. 자리를 여기서 계산하지 않고
    # 아는 쪽(워커)이 말해 주는 값을 그대로 받는다 — 규칙이 두 곳에 생기면 갈린다.
    # 없어도 된다(분석은 성공한 것이고, 화면이 리포트를 못 찾을 뿐이다).
    # 🔴 `succeeded` 가 아니면 무시된다(실패한 작업이 가리킬 리포트는 없다).
    # 상한은 S3 객체 키 한계(1024바이트)다.
    report_key: str | None = Field(default=None, max_length=1024)
