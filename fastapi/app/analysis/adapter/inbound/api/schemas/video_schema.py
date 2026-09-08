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
    # 원본 파일 이름. 저장 키를 사람이 알아볼 수 있게 짓는 데 쓴다(미결 `jin`
    # 24번). 슬러그화되므로 이상한 문자여도 안전하다.
    filename: str = Field(min_length=1, max_length=255)


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

    `analyze` 가 거짓이면 규격은 검사하되 분석 작업을 만들지 않는다. 기록으로
    남기려고 올리는 클립("업로드 영상")과 실력을 재려고 올리는 클립을 가르는
    자리다. 생략하면 참 — 안 보내던 클라이언트의 동작이 그대로다.
    """

    sport_code: str = Field(min_length=1, max_length=20)
    storage_key: str = Field(min_length=1, max_length=255)
    duration_ms: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    side: str | None = Field(default=None, max_length=5)
    analyze: bool = True
    # 원본 파일 이름. DB 에 온전히 남긴다 — 저장 키는 슬러그라 손실적이다(jin 24).
    filename: str | None = Field(default=None, max_length=255)


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
    is_public: bool
    title: str | None
    description: str | None
    kept: bool


class UpdateVideoSchema(BaseModel):
    """클립을 부분 수정한다. `PATCH /videos/{id}` 본문.

    셋 다 생략 가능하다 — **보낸 것만** 바뀐다(`model_fields_set` 로 가른다).
    `title`·`description` 은 `null` 이나 공백만 보내면 지운다.
    """

    is_public: bool | None = None
    title: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=280)


class PlaybackUrlResponse(BaseModel):
    """재생용 사전 서명 GET URL. `url` 에 바로 GET 하면 원본이 온다."""

    url: str
    expires_in: int


class PublicVideoResponse(BaseModel):
    """홈 영상 모음 한 줄. **저장 키·업로더는 안 실린다** — 저장 키에 업로더
    `user_id` 가 들어 있고, 재생은 `GET /videos/{id}/playback-url` 로 따로 받는다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sport_code: str
    duration_ms: int | None
    created_at: Rfc3339
    title: str | None
    description: str | None


class AdminVideoRowResponse(BaseModel):
    """관리자 영상 목록 한 줄. **사람이 읽을 수 있게** 원본 이름·업로드일·상태를
    싣고, S3 로 되짚을 `storage_key` 와 리포트 폴더 접두사를 함께 준다 — 목록에서
    N개 객체마다 사전 서명을 하지 않으려는 것이다(재생·리포트는 이 값으로 짚는다).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sport_code: str
    original_filename: str | None
    storage_key: str
    created_at: Rfc3339
    kept: bool
    is_public: bool
    passed: bool
    reject_reason: str | None
    analysis_status: str | None
    report_prefix: str


class AdminVideoListResponse(BaseModel):
    """한 사람(`?user=<uid|email>`)의 영상 전부. 닉네임·이메일은 **현재 값**이다
    (DB 조인이라 rename 이 반영된다 — 옛 저장 키에 얼어붙은 닉네임과 다르다).
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nickname: str
    email: str
    items: list[AdminVideoRowResponse]
