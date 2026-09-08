"""영상 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class UploadUrlCommand:
    """올리기 전에 자리를 받는다. 파일은 아직 없다."""

    user_id: UUID
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class UploadUrlResult:
    storage_key: str
    upload_url: str
    expires_in: int


@dataclass(frozen=True)
class RegisterVideoCommand:
    """올린 뒤 등록한다.

    `width`·`height`·`duration_ms` 는 **클라이언트가 잰 값**이다. 서버가 다시
    재려면 원본을 내려받아야 하고 그러면 PER-002(업로드·재생이 앱 서버를 지나지
    않는다)가 무너진다. 용량만은 저장소에 물어 실측한다 — 사전 서명 URL 이
    크기를 강제하지 못하기 때문이다.

    `analyze` 가 거짓이면 규격 검사는 하되 분석 작업을 만들지 않는다.
    """

    user_id: UUID
    sport_code: str
    storage_key: str
    duration_ms: int
    width: int
    height: int
    side: str | None = None
    analyze: bool = True


@dataclass(frozen=True)
class MyVideosQuery:
    user_id: UUID


@dataclass(frozen=True)
class SetVisibilityCommand:
    """클립의 공개 여부를 바꾼다. **자기 클립만** — `user_id` 로 소유를 확인한다."""

    video_id: UUID
    user_id: UUID
    is_public: bool


@dataclass(frozen=True)
class PublicVideosQuery:
    """홈의 영상 모음. 공개 클립만, 최근 것부터."""

    limit: int = 100


@dataclass(frozen=True)
class VideoResult:
    """`/videos` 화면 한 줄. 분석 상태와 반려 사유가 같이 온다.

    `passed` 가 거짓이면 `analysis_job_id` 는 없다 — 반려된 클립은 분석하지
    않는다. 그것이 규격 검사를 두는 이유다.
    """

    id: UUID
    sport_code: str
    storage_key: str
    duration_ms: int | None
    side: str | None
    created_at: datetime
    passed: bool
    reject_reason: str | None
    analysis_job_id: UUID | None
    analysis_status: str | None
    is_public: bool


@dataclass(frozen=True)
class PublicVideoResult:
    """공개 목록 한 줄. **저장 키·업로더를 싣지 않는다** — 재생 주소(사전
    서명)와 제목은 아직 없다(미결 `paik` 5번의 3·4 조각).
    """

    id: UUID
    sport_code: str
    duration_ms: int | None
    created_at: datetime
