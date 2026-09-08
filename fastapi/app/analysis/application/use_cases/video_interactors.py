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

import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.analysis.application.dtos.video_dto import (
    UNSET,
    AdminDeleteVideoCommand,
    AdminVideoListResult,
    AdminVideoRow,
    AdminVideosQuery,
    DeleteVideoCommand,
    GetPlaybackUrlCommand,
    KeepVideoCommand,
    MyVideosQuery,
    PlaybackUrlResult,
    PublicVideoResult,
    PublicVideosQuery,
    RegisterVideoCommand,
    UpdateVideoCommand,
    UploadUrlCommand,
    UploadUrlResult,
    VideoResult,
)
from app.analysis.application.ports.input.video_use_cases import (
    AdminDeleteVideoUseCase,
    CreateUploadUrlUseCase,
    DeleteVideoUseCase,
    GetPlaybackUrlUseCase,
    KeepVideoUseCase,
    ListAdminVideosUseCase,
    ListMyVideosUseCase,
    ListPublicVideosUseCase,
    RegisterVideoUseCase,
    UpdateVideoUseCase,
)
from app.analysis.application.ports.output.storage_port import StoragePort
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.application.use_cases.video_assembler import (
    to_public_video_result,
    to_video_result,
)
from app.analysis.domain.entities.video_entity import ValidationEntity, VideoEntity
from app.analysis.domain.rules.video_rules import (
    MAX_BYTES,
    build_storage_key,
    extension_for,
    is_provisional_key,
    owns_key,
    reject_reason,
    report_source_key,
)
from app.core.errors import ApiError

_log = logging.getLogger("supersub.analysis")

# 새 작업의 첫 상태. 값 목록은 `analysis_job` ORM 의 주석에 있다.
_QUEUED = "queued"


class CreateUploadUrlInteractor(CreateUploadUrlUseCase):
    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
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

        storage_key = build_storage_key(
            command.user_id,
            extension,
            nickname=self._repository.uploader_nickname(command.user_id) or "",
            original_filename=command.filename,
        )
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
            analyze=command.analyze,
        )
        now = datetime.now(timezone.utc)
        # 반려된 클립은 분석하지 않는다(규격 검사를 두는 이유). `analyze=False` 면
        # 규격은 통과해도 작업을 만들지 않는다 — 기록용 업로드(미결 `paik` 4번).
        make_job = reason is None and command.analyze
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
            analysis_job_id=uuid4() if make_job else None,
            analysis_status=_QUEUED if make_job else None,
            # 미결 `jin` 24번 — 지금은 전부 저장된 상태로 둔다(동작 보존).
            # 프론트가 `keep` 을 부를 준비가 되면 `kept = not command.analyze` 로
            # 켠다(jin 24 5조각). 그전에 켜면 `/analysis` 업로드가 프로필에서
            # 사라지고 되살릴 길이 없다.
            kept=True,
            original_filename=command.original_filename,
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


def _clean_text(value: object) -> str | None:
    """빈 문자열·공백만 있는 값은 지운 것으로 본다 — `PATCH /me/card` 의
    `tagline` 과 같은 판단이다. `None` 은 그대로 `None`.
    """
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


class UpdateVideoInteractor(UpdateVideoUseCase):
    def __init__(self, repository: VideoPort) -> None:
        self._repository = repository

    def __call__(self, command: UpdateVideoCommand) -> VideoResult:
        video = self._repository.update_video(
            command.video_id,
            command.user_id,
            is_public=command.is_public,
            title=(
                UNSET if command.title is UNSET else _clean_text(command.title)
            ),
            description=(
                UNSET
                if command.description is UNSET
                else _clean_text(command.description)
            ),
        )
        if video is None:
            # 남의 클립인지 없는 클립인지 구별해 주지 않는다 — 남의 클립 존재
            # 여부가 새어 나가지 않게.
            raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")
        return to_video_result(video)


class ListPublicVideosInteractor(ListPublicVideosUseCase):
    def __init__(self, repository: VideoPort) -> None:
        self._repository = repository

    def __call__(self, query: PublicVideosQuery) -> list[PublicVideoResult]:
        return [
            to_public_video_result(v)
            for v in self._repository.list_public(query.limit)
        ]


class GetPlaybackUrlInteractor(GetPlaybackUrlUseCase):
    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, command: GetPlaybackUrlCommand) -> PlaybackUrlResult:
        video = self._repository.get(command.video_id)
        if video is None or not (
            video.is_public or video.user_id == command.user_id
        ):
            # 비공개 남의 클립은 "없음"과 같게 답한다.
            raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")
        url, expires_in = self._storage.create_download_url(video.storage_key)
        return PlaybackUrlResult(url=url, expires_in=expires_in)


class DeleteVideoInteractor(DeleteVideoUseCase):
    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, command: DeleteVideoCommand) -> None:
        video = self._repository.delete(command.video_id, command.user_id)
        if video is None:
            raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")
        # 🔴 DB 에서 사라진 것이 "사용자에게 없어진 것"이다. S3 정리는 best-effort —
        #    IAM 에 `s3:DeleteObject` 가 붙기 전에는 실패하지만(미결 `jin` 24번 IAM
        #    조각), 남은 객체는 백스톱 스윕이 잡는다. 여기서 500 을 내면 이미 지운
        #    행을 두고 재시도를 부른다.
        _cleanup_storage(self._storage, video)


class KeepVideoInteractor(KeepVideoUseCase):
    """"내 프로필에 리포트 저장" — `kept` 를 켜고 임시 원본을 리포트 자리로 옮긴다.

    순서가 중요하다: **S3 이동을 먼저** 하고 그다음 DB 를 맞춘다. 반대로 하면
    DB 는 새 키를 가리키는데 객체가 아직 옛 자리에 있는 창이 생긴다. 이동이
    실패하면 DB 는 그대로라 그냥 다시 부르면 되고, 이동 뒤 DB 가 실패하면 객체는
    `reports/<video_id>/` 아래라 삭제·스윕이 접두사로 잡는다.
    """

    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, command: KeepVideoCommand) -> VideoResult:
        video = self._repository.get(command.video_id)
        if video is None or video.user_id != command.user_id:
            # 남의 클립인지 없는 클립인지 구별해 주지 않는다.
            raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")

        new_key = video.storage_key
        # 리포트가 딸린 분석 클립의 임시 원본만 옮긴다. `/me` 업로드(기록용,
        # 분석 작업 없음)는 `videos/` 에 그대로 둔다 — 옮길 리포트 폴더가 없다.
        if video.analysis_job_id is not None and is_provisional_key(
            video.storage_key
        ):
            new_key = report_source_key(video.user_id, video.id, video.storage_key)
            self._storage.move_object(video.storage_key, new_key)

        updated = self._repository.mark_kept(
            command.video_id, command.user_id, storage_key=new_key
        )
        if updated is None:
            # 그 사이 지워졌다(경합). 이동을 되돌리지 않는다 — reports 접두사라
            # 스윕이 잡고, 여기서 롤백을 시도하면 더 꼬인다.
            raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")
        return to_video_result(updated)


def _cleanup_storage(storage: StoragePort, video: VideoEntity) -> None:
    """지운 영상의 S3 객체·리포트 폴더를 정리한다. **best-effort** — 실패해도
    DB 에서 사라진 것이 "없어진 것"이고, 남은 객체는 백스톱 스윕이 잡는다.
    """
    try:
        storage.delete_object(video.storage_key)
        storage.delete_prefix(f"reports/{video.user_id}/{video.id}/")
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "video %s: DB 는 지웠으나 S3 정리 실패 (%s: %s)",
            video.id,
            type(exc).__name__,
            exc,
        )


def _to_admin_row(video: VideoEntity) -> AdminVideoRow:
    validation = video.validation
    return AdminVideoRow(
        id=video.id,
        sport_code=video.sport_code,
        original_filename=video.original_filename,
        storage_key=video.storage_key,
        created_at=video.created_at,
        kept=video.kept,
        is_public=video.is_public,
        passed=bool(validation and validation.passed),
        reject_reason=validation.reject_reason if validation else None,
        analysis_status=video.analysis_status,
        report_prefix=f"reports/{video.user_id}/{video.id}/",
    )


class ListAdminVideosInteractor(ListAdminVideosUseCase):
    def __init__(self, repository: VideoPort) -> None:
        self._repository = repository

    def __call__(self, query: AdminVideosQuery) -> AdminVideoListResult:
        ref = self._repository.resolve_user(query.identifier.strip())
        if ref is None:
            raise ApiError(
                404, "USER_NOT_FOUND", "해당 사용자를 찾을 수 없습니다."
            )
        rows = self._repository.list_all_by_user(ref.id)
        return AdminVideoListResult(
            user_id=ref.id,
            nickname=ref.nickname,
            email=ref.email,
            items=[_to_admin_row(v) for v in rows],
        )


class AdminDeleteVideoInteractor(AdminDeleteVideoUseCase):
    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, command: AdminDeleteVideoCommand) -> None:
        video = self._repository.admin_delete(command.video_id)
        if video is None:
            raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")
        # 비밀번호를 안 받는 대신 누가 눌렀는지 남긴다(`DELETE /admin/users` 와 같은 결).
        _log.info(
            "event=admin_delete_video admin_id=%s video_id=%s",
            command.admin_id,
            video.id,
        )
        _cleanup_storage(self._storage, video)
