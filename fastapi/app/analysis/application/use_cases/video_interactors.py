"""영상 인터랙터. 규격 판단은 `domain/rules/video_rules.py` 가 한다.

## 반려는 실패가 아니다

규격에 안 맞는 클립을 422 로 돌려보내면 **사유가 아무 데도 안 남는다.** SFR-001
이 요구하는 것은 그 반대다 — 사유를 값으로 기록해 검수 기준을 나중에 확인할 수
있게 하는 것. 그래서 반려도 `201 Created` 로 답하고 `passed: false` 와 사유를
본문에 싣는다. **등록은 성공했고, 그 클립이 분석 대상이 아닐 뿐이다.**

422 로 내는 것은 **등록 자체가 성립하지 않는 경우**뿐이다: 종목이 없다, 파일이
안 올라와 있다, 남의 저장 키다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.analysis.application.dtos.video_dto import (
    MyVideosQuery,
    RegisterVideoCommand,
    UploadUrlCommand,
    UploadUrlResult,
    VideoResult,
)
from app.analysis.application.ports.input.video_use_cases import (
    CreateUploadUrlUseCase,
    ListMyVideosUseCase,
    RegisterVideoUseCase,
)
from app.analysis.application.ports.output.storage_port import StoragePort
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.application.use_cases.video_assembler import to_video_result
from app.analysis.domain.entities.video_entity import ValidationEntity, VideoEntity
from app.analysis.domain.rules.video_rules import (
    MAX_BYTES,
    build_storage_key,
    extension_for,
    owns_key,
    reject_reason,
)
from app.core.errors import ApiError

# 새 작업의 첫 상태. 값 목록은 `analysis_job` ORM 의 주석에 있다.
_QUEUED = "queued"


class CreateUploadUrlInteractor(CreateUploadUrlUseCase):
    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    def __call__(self, command: UploadUrlCommand) -> UploadUrlResult:
        extension = extension_for(command.content_type)
        if extension is None:
            raise ApiError(
                422,
                "UNSUPPORTED_FORMAT",
                "지원하지 않는 형식입니다. mp4 또는 mov 로 올려 주십시오.",
            )

        # 여기서 거르는 것은 **헛걸음을 줄이기 위한 것**이다. 사전 서명 URL 은
        # 크기를 강제하지 못하므로 진짜 상한은 등록할 때 실측으로 건다.
        if command.size_bytes > MAX_BYTES:
            raise ApiError(
                422,
                "FILE_TOO_LARGE",
                f"용량 상한은 {MAX_BYTES // (1024 * 1024)}MB 입니다.",
            )

        storage_key = build_storage_key(command.user_id, extension)
        url, expires_in = self._storage.create_upload_url(
            storage_key, command.content_type
        )
        return UploadUrlResult(
            storage_key=storage_key, upload_url=url, expires_in=expires_in
        )


class RegisterVideoInteractor(RegisterVideoUseCase):
    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, command: RegisterVideoCommand) -> VideoResult:
        if not self._repository.sport_exists(command.sport_code):
            raise ApiError(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다.")

        # 🔴 키에 업로더가 들어 있으므로 대조할 수 있다. 안 하면 남이 올린
        #    객체의 키를 자기 영상으로 등록할 수 있다.
        if not owns_key(command.user_id, command.storage_key):
            raise ApiError(403, "FORBIDDEN", "다른 사용자에게 발급된 저장 키입니다.")

        size_bytes = self._storage.size_of(command.storage_key)
        if size_bytes is None:
            # 반려가 아니다 — 검사할 파일이 없다. 반려로 기록하면 "규격에 안 맞는
            # 영상"과 "안 올린 영상"이 같아 보인다.
            raise ApiError(
                422, "FILE_NOT_UPLOADED", "그 키에 올라온 파일이 없습니다."
            )

        reason = reject_reason(
            duration_ms=command.duration_ms,
            width=command.width,
            height=command.height,
            size_bytes=size_bytes,
        )
        now = datetime.now(timezone.utc)
        video = VideoEntity(
            id=uuid4(),
            user_id=command.user_id,
            sport_code=command.sport_code,
            storage_key=command.storage_key,
            duration_ms=command.duration_ms,
            side=command.side,
            created_at=now,
            validation=ValidationEntity(
                passed=reason is None, reject_reason=reason, checked_at=now
            ),
            # 반려된 클립은 분석하지 않는다 — 규격 검사를 두는 이유가 그것이다.
            analysis_job_id=None if reason else uuid4(),
            analysis_status=None if reason else _QUEUED,
        )
        self._repository.register(video)
        return to_video_result(video)


class ListMyVideosInteractor(ListMyVideosUseCase):
    def __init__(self, repository: VideoPort) -> None:
        self._repository = repository

    def __call__(self, query: MyVideosQuery) -> list[VideoResult]:
        return [
            to_video_result(v) for v in self._repository.list_by_user(query.user_id)
        ]
