"""영상 유스케이스가 주고받는 DTO. **원시 타입만** 담는다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final
from uuid import UUID

# `PATCH /videos/{id}` 는 부분 수정이라 "안 보냄"과 "null 로 지움"을 구별해야
# 한다. 기본값이 None 이면 둘이 같아진다 — 그래서 별도 표식을 둔다.
UNSET: Final[Any] = object()


@dataclass(frozen=True)
class UploadUrlCommand:
    """올리기 전에 자리를 받는다. 파일은 아직 없다."""

    user_id: UUID
    content_type: str
    size_bytes: int
    filename: str = ""  # 원본 이름 — 저장 키를 사람이 알아보게 짓는다(jin 24)


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
    original_filename: str | None = None  # 원본 이름 — DB 에 온전히 남긴다(jin 24)
    # 「이 사람으로 분석」 (미결 `paik` 6번). 정규화 `[x, y, w, h]`(0~1)와 그 시각(ms).
    # 스키마가 정규화·기하 검증을 끝낸 값이다. 지정이 없으면 둘 다 None.
    subject_box: list[float] | None = None
    subject_at_ms: int | None = None
    # 「집중해서 볼 항목」 (미결 `paik` 8번). 루브릭 criteria id 리스트.
    # 스키마가 정리(공백 제거·중복 제거)한 값. 비면 None(「전체」).
    focus: list[str] | None = None


@dataclass(frozen=True)
class MyVideosQuery:
    user_id: UUID


@dataclass(frozen=True)
class UpdateVideoCommand:
    """클립을 부분 수정한다. **자기 클립만** — `user_id` 로 소유를 확인한다.

    각 필드는 `UNSET` 이면 건드리지 않고, 값(또는 `None`)이면 그 값으로 바꾼다.
    `title`·`description` 은 `None`/공백이면 지운다.
    """

    video_id: UUID
    user_id: UUID
    is_public: bool | Any = UNSET
    title: str | None | Any = UNSET
    description: str | None | Any = UNSET
    # 「대표 영상」 토글 (미결 `paik` 10번). True 로 세우면 그 사람의 다른 대표는
    # 내려간다. 반려된 클립엔 못 세운다(422).
    is_featured: bool | Any = UNSET


@dataclass(frozen=True)
class GetPlaybackUrlCommand:
    """재생용 사전 서명 URL 을 받는다. 공개 클립이거나 자기 클립일 때만."""

    video_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class PlaybackUrlResult:
    url: str
    expires_in: int


@dataclass(frozen=True)
class GetFeaturedVideoCommand:
    """어떤 사람의 대표 영상을 그 사람의 **카드 슬러그**로 가져온다 (미결 `paik` 10번).

    로그인한 사람이면 누구나 볼 수 있다 — 대표는 「보여 주려고」 고른 장면이지만,
    사전 서명 URL 을 내주는 자리라 익명 긁기는 막는다.
    """

    card_public_slug: str


@dataclass(frozen=True)
class FeaturedVideoResult:
    video_id: UUID
    url: str
    expires_in: int
    sport_code: str
    duration_ms: int | None


@dataclass(frozen=True)
class DeleteVideoCommand:
    """영상을 지운다. **자기 클립만** — `user_id` 로 소유를 확인한다."""

    video_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class KeepVideoCommand:
    """"내 프로필에 리포트 저장". `kept` 를 켜고, 임시 원본(`videos/…`)이면
    리포트 자리(`reports/<user_id>/<video_id>/source.<ext>`)로 옮긴다(미결 `jin`
    24번). **자기 클립만.**
    """

    video_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class PublicVideosQuery:
    """홈의 영상 모음. 공개 클립만, 최근 것부터."""

    limit: int = 100


@dataclass(frozen=True)
class UserRef:
    """`user` 컨텍스트에서 원시 SQL 로 읽어 온 사람 1명. 관리자 영상 목록이
    `?user=<uid|email>` 를 사람으로 되짚는 데 쓴다(미결 `jin` 24번).
    """

    id: UUID
    nickname: str
    email: str


@dataclass(frozen=True)
class AdminVideosQuery:
    """관리자가 한 사람의 영상을 전부 본다. `identifier` 는 `user.id`(UUID 문자열)
    또는 이메일이다.
    """

    identifier: str


@dataclass(frozen=True)
class AdminVideoRow:
    """관리자 목록 한 줄. **사람이 읽을 수 있게** 원본 이름·업로드일·상태를 싣고,
    S3 로 되짚을 `storage_key` 와 리포트 폴더 접두사를 함께 준다.
    """

    id: UUID
    sport_code: str
    original_filename: str | None
    storage_key: str
    created_at: datetime
    kept: bool
    is_public: bool
    passed: bool
    reject_reason: str | None
    analysis_status: str | None
    report_prefix: str


@dataclass(frozen=True)
class AdminVideoListResult:
    """한 사람의 영상 전부. 닉네임·이메일은 **현재 값**이다 — 옛 저장 키에 얼어
    붙은 닉네임과 달리 DB 조인이라 rename 이 반영된다(미결 `jin` 24번).
    """

    user_id: UUID
    nickname: str
    email: str
    items: list[AdminVideoRow]


@dataclass(frozen=True)
class AdminDeleteVideoCommand:
    """관리자가 **아무** 영상이나 지운다. 소유 검사가 없다 — 관리자 인증이 그
    자리를 대신한다(`DELETE /admin/users/{id}` 와 같은 결). 누가 눌렀는지는
    로그에 남긴다.
    """

    video_id: UUID
    admin_id: UUID


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
    is_featured: bool
    title: str | None
    description: str | None
    kept: bool


@dataclass(frozen=True)
class PublicVideoResult:
    """공개 목록 한 줄. **저장 키·업로더를 싣지 않는다** — 저장 키에 업로더
    `user_id` 가 들어 있고, 재생은 `GET /videos/{id}/playback-url` 로 따로 받는다.
    """

    id: UUID
    sport_code: str
    duration_ms: int | None
    created_at: datetime
    title: str | None
    description: str | None
