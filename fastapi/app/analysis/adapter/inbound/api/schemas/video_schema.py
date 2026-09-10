"""영상 HTTP 모델. 계약 문서 3-5절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    # 「이 사람으로 분석」 (미결 `paik` 6번). 정규화 `[x, y, w, h]` (0~1) 와 그
    # 박스를 그린 영상 시각(ms). 🔴 **정규화 좌표만** — 화면 픽셀을 보내면 422 다
    # (조용히 클램프하면 엉뚱한 사람을 분석하고도 "지정대로 했다"고 답한다).
    # 지정이 없으면 둘 다 생략한다 — 「자동으로 고르기」가 정식 경로다.
    subject_box: list[float] | None = Field(default=None, min_length=4, max_length=4)
    subject_at_ms: int | None = Field(default=None, ge=0)

    # 「집중해서 볼 항목」 (미결 `paik` 8번). 루브릭 `criteria[].id` 리스트
    # (예: `["follow_through", "guide_hand"]`). 🔴 **빈 목록·생략 = 「전체적으로」**
    # 가 기본이자 가장 흔한 경우다 — 실패로 만들지 않는다. 각 항목의 실재
    # 여부는 서버가 못 본다(루브릭은 `agent/`) — 형식만 본다(공백·중복 정리).
    focus: list[str] | None = Field(default=None, max_length=24)

    @model_validator(mode="after")
    def _clean_focus(self) -> "RegisterVideoSchema":
        if self.focus is None:
            return self
        seen: list[str] = []
        for raw in self.focus:
            item = raw.strip()
            if not item:
                continue
            if len(item) > 40:
                raise ValueError("focus 항목이 너무 깁니다(40자 상한).")
            if item not in seen:
                seen.append(item)
        self.focus = seen or None
        return self

    @model_validator(mode="after")
    def _check_subject(self) -> "RegisterVideoSchema":
        box, at = self.subject_box, self.subject_at_ms
        if (box is None) != (at is None):
            raise ValueError(
                "subject_box 와 subject_at_ms 는 함께 주거나 함께 생략합니다."
            )
        if box is None:
            return self
        x, y, w, h = box
        if not all(0.0 <= v <= 1.0 for v in box):
            raise ValueError("subject_box 는 정규화 좌표입니다(0~1). 픽셀이 아닙니다.")
        if w <= 0 or h <= 0:
            raise ValueError("subject_box 의 너비·높이는 0보다 커야 합니다.")
        if x + w > 1.0 or y + h > 1.0:
            raise ValueError("subject_box 가 화면을 벗어납니다.")
        if at is not None and at > self.duration_ms:
            raise ValueError("subject_at_ms 가 클립 길이를 벗어납니다.")
        return self


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
    is_featured: bool


class UpdateVideoSchema(BaseModel):
    """클립을 부분 수정한다. `PATCH /videos/{id}` 본문.

    셋 다 생략 가능하다 — **보낸 것만** 바뀐다(`model_fields_set` 로 가른다).
    `title`·`description` 은 `null` 이나 공백만 보내면 지운다.
    """

    is_public: bool | None = None
    title: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=280)
    # 「대표 영상」 토글 (미결 `paik` 10번). `true` 로 세우면 그 사람의 다른 대표는
    # 자동으로 내려간다(사람당 하나). 반려된 클립엔 못 세운다(422 `CANNOT_FEATURE`).
    is_featured: bool | None = None


class PlaybackUrlResponse(BaseModel):
    """재생용 사전 서명 GET URL. `url` 에 바로 GET 하면 원본이 온다."""

    url: str
    expires_in: int


class FeaturedVideoResponse(BaseModel):
    """어떤 사람의 대표 영상 하나(미결 `paik` 10번). `GET /cards/{slug}/featured-video`.

    저장 키가 아니라 **사전 서명 GET URL** 을 준다 — 버킷은 닫혀 있다(5번과 같은 원칙).
    대표가 없으면 이 응답이 아니라 `404 NO_FEATURED_VIDEO` 다.
    """

    model_config = ConfigDict(from_attributes=True)

    video_id: UUID
    url: str
    expires_in: int
    sport_code: str
    duration_ms: int | None


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


class ReportCriterionResponse(BaseModel):
    """리포트 항목 하나. 🔴 `band`·`stat`·가중치는 없다 — 임계값이 검수 전이고
    (미결 24번) 수치는 카드 경로가 따로 읽는다.
    """

    model_config = ConfigDict(from_attributes=True)

    criterion_id: str
    name: str
    grade: int | None  # None = 제외. 0 점이 아니다.
    title: str | None
    evidence: str | None
    metric_ref: str | None
    skipped: bool


class ReportSceneResponse(BaseModel):
    """판단의 근거가 된 장면. `at_seconds` 로 그 시각으로 이동한다."""

    model_config = ConfigDict(from_attributes=True)

    metric_code: str
    label: str
    at_seconds: float


class VideoReportResponse(BaseModel):
    """적재된 분석 리포트(미결 `jin` 27번 · `paik` 7번). `GET /videos/{id}/report`.

    🔴 **허용목록이다** — DB 조립(계약 3-1). 총점·등급 숫자는 `summary` 에 없고
    (3장 4) 항목별 등급·`stat` 도 여기 없다(카드 경로가 읽는다).
    """

    model_config = ConfigDict(from_attributes=True)

    video_id: UUID
    analyzed_at: Rfc3339
    summary: str
    provisional: bool | None
    breakdown: list[ReportCriterionResponse]
    scenes: list[ReportSceneResponse]
    previews: dict[str, str] | None
    keypoint_quality: dict[str, object] | None
