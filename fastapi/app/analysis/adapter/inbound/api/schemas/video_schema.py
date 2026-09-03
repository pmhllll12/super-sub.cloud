"""영상 HTTP 모델. 계약 문서 3-5절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.shared import Rfc3339


class UploadUrlSchema(BaseModel):
    """올릴 자리를 받는다.

    `size_bytes` 는 **헛걸음을 줄이려고** 미리 받는 값이다. 사전 서명 URL 은
    크기를 강제하지 못하므로 진짜 상한은 등록할 때 저장소에 물어 건다.
    """

    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=1)


class UploadUrlResponse(BaseModel):
    """`upload_url` 에 **PUT** 한다. `Content-Type` 헤더를 요청한 값 그대로
    보내야 한다 — 서명에 들어 있어서 다르면 S3 가 거절한다.
    """

    model_config = ConfigDict(from_attributes=True)

    storage_key: str
    upload_url: str
    expires_in: int


class RegisterVideoSchema(BaseModel):
    """올린 뒤 등록한다.

    `duration_ms`·`width`·`height` 는 **클라이언트가 잰 값**이다. 서버가 다시
    재려면 원본을 내려받아야 하고 그러면 PER-002 가 무너진다.

    `side` 는 던지는 팔·차는 발이다. 자동 판별이 팔 종목에서 신뢰할 수 없어
    (5장 CON-007) 사람이 지정할 수 있게 열어 둔다. 생략하면 자동 판별을 쓴다.
    """

    sport_code: str = Field(min_length=1, max_length=20)
    storage_key: str = Field(min_length=1, max_length=255)
    duration_ms: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    side: str | None = Field(default=None, max_length=5)


class VideoResponse(BaseModel):
    """영상 1건.

    🔴 **`passed` 가 거짓이어도 실패 응답이 아니다.** 등록은 됐고 그 클립이
    분석 대상이 아닐 뿐이다. 사유는 `reject_reason` 에 있다(SFR-001 — 사유를
    값으로 남긴다). 클라이언트는 `passed` 로 분기한다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sport_code: str
    storage_key: str
    duration_ms: int | None
    side: str | None
    created_at: Rfc3339
    passed: bool
    reject_reason: str | None
    analysis_job_id: UUID | None
    analysis_status: str | None
