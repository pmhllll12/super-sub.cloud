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
    CardGradeResult,
    DeleteVideoCommand,
    FeaturedVideoResult,
    GetCardGradeCommand,
    GetFeaturedVideoCommand,
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
    GetCardGradeUseCase,
    GetFeaturedVideoUseCase,
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
from app.analysis.domain.rules.grade_rules import display_grade, is_trust_dominant
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
        # 🔴 「없는 종목」과 **「지금 안 받는 종목」을 가른다**(`ho` 39번).
        # 루브릭이 없는 종목은 등록은 통과하고 **워커에서 거부**돼서, 사용자
        # 입장에서는 올라간 뒤에야 실패한다. 올리기 전에 막는 편이 맞다.
        if not self._repository.sport_is_active(command.sport_code):
            raise ApiError(
                422, "SPORT_NOT_AVAILABLE", "지금은 받지 않는 종목입니다."
            )

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

        # 재업로드 감지(`ho` 41번) — 규격을 통과한, 실제로 분석할 클립만
        # 본다. 「이 사람으로 분석」·「집중해서 볼 항목」을 지정하면 같은
        # 영상이어도 측정 대상이 달라질 수 있어 대상에서 뺀다.
        content_hash = self._storage.content_hash_of(command.storage_key)
        prior = None
        if (
            reason is None
            and command.analyze
            and content_hash is not None
            and command.subject_box is None
            and not command.focus
        ):
            prior = self._repository.find_prior_outcome(
                command.user_id, content_hash
            )

        # 반려된 클립은 분석하지 않는다(규격 검사를 두는 이유). `analyze=False` 면
        # 규격은 통과해도 작업을 만들지 않는다 — 기록용 업로드(미결 `paik` 4번).
        # 같은 내용을 이미 분석해 본 적이 있으면(`prior`) 새 작업도 안 만든다 —
        # 결정론적 파이프라인이라 같은 파일은 다시 돌려도 같은 결과다.
        make_job = reason is None and command.analyze and prior is None
        # 「이미 결과가 있다」도 「작업이 있다」와 같은 취급이다 — 임시 상태로
        # 뒀다가 사용자가 「내 프로필에 저장」을 눌러야 영구가 된다.
        has_outcome = make_job or prior is not None
        video = VideoEntity(
            id=uuid4(),
            user_id=command.user_id,
            sport_code=command.sport_code,
            storage_key=command.storage_key,
            duration_ms=command.duration_ms,
            side=command.side,
            created_at=now,
            width=command.width,
            height=command.height,
            validation=ValidationEntity(
                passed=reason is None, reject_reason=reason, checked_at=now
            ),
            analysis_job_id=uuid4() if make_job else None,
            analysis_status=_QUEUED if make_job else None,
            # 미결 `jin` 24번 5조각 해소(2026-09-11, 사용자 지적 — 분석에
            # 실패한 영상이 지워지지 않고 남는다). **작업이 생긴 클립만**
            # 임시다 — 그 클립만 나중에 "리포트가 나오나"가 갈리기 때문이다.
            # `analyze=False`(기록용 업로드)와 **반려**(작업 자체가 안
            # 생긴다 — `reject_reason`을 보여줄 뿐 이후 상태가 안 바뀐다)는
            # 처음부터 영구다. `www`가 `POST /videos/{id}/keep`(「내 프로필에
            # 리포트 저장」)을 부를 때만 임시 클립이 영구가 된다. 그전까지는
            # 화면을 벗어나면 즉시 `DELETE /videos/{id}`가, 그것도 놓치면
            # (브라우저가 죽는 등) `provisional_video_ttl_hours` 백스톱이
            # 지운다 — 분석에 실패해 다시 볼 리포트가 없는 클립이 여기 걸린다.
            #
            # 🔴 `not command.analyze` 가 아니라 `not has_outcome` 이다 —
            # `analyze=True` 인데 반려된 클립까지 임시로 두면 방금 반려된
            # 사유를 보여준 그 클립이 목록에서 곧장 사라진다(`_by_user` 의
            # `kept_only=True` 필터, `test_반려_사유가_목록에도_온다`). 이미
            # 결과를 재사용한 중복도 같은 이유로 임시다(`ho` 41번).
            kept=not has_outcome,
            original_filename=command.original_filename,
            # 미결 `paik` 6번. 작업을 안 만들면(반려·`analyze=False`) 저장소가
            # 버린다 — 담을 `analysis_job` 행이 없다. 지정이 없을 때 실패로
            # 만들지 않는 것이 이 항목의 「하지 말 것」이다.
            subject_box=command.subject_box if make_job else None,
            subject_at_ms=command.subject_at_ms if make_job else None,
            focus=command.focus if make_job else None,
            content_hash=content_hash,
            duplicate_of_video_id=prior.video_id if prior else None,
            duplicate_status=prior.status if prior else None,
            duplicate_failure_reason=prior.failure_reason if prior else None,
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
        # 🔴 대표로 **세우기 전에** 반려 여부를 본다 — 반려된 클립은 서버가 안
        #    보는 영상이라(미결 `paik` 10번), 대표가 되면 추천 판이 없는 것을
        #    읽으러 간다. 내리기(`False`)·안 건드림(`UNSET`)은 확인이 필요 없다.
        if command.is_featured is True:
            existing = self._repository.get(command.video_id)
            if existing is None or existing.user_id != command.user_id:
                raise ApiError(404, "VIDEO_NOT_FOUND", "클립을 찾을 수 없습니다.")
            if not (existing.validation and existing.validation.passed):
                raise ApiError(
                    422, "CANNOT_FEATURE", "반려된 클립은 대표로 세울 수 없습니다."
                )

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
            is_featured=command.is_featured,
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
        videos = self._repository.list_public(query.limit)
        # 업로더는 영상별로 한 번씩이 아니라 배치로 구한다(N+1 방지) — `paik` 16번.
        uploaders = self._repository.uploader_info(
            list({v.user_id for v in videos})
        )
        return [
            to_public_video_result(v, *uploaders.get(v.user_id, ("", None)))
            for v in videos
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


class GetFeaturedVideoInteractor(GetFeaturedVideoUseCase):
    def __init__(self, repository: VideoPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, command: GetFeaturedVideoCommand) -> FeaturedVideoResult:
        video = self._repository.find_featured_by_card_slug(
            command.card_public_slug
        )
        if video is None:
            # 슬러그가 없든·대표가 없든·반려됐든 밖에서는 다 "없음"이다.
            raise ApiError(
                404, "NO_FEATURED_VIDEO", "대표 영상이 없습니다."
            )
        url, expires_in = self._storage.create_download_url(video.storage_key)
        return FeaturedVideoResult(
            video_id=video.id,
            url=url,
            expires_in=expires_in,
            sport_code=video.sport_code,
            duration_ms=video.duration_ms,
        )


class GetCardGradeInteractor(GetCardGradeUseCase):
    """미결 `paik` 25·26번. 경계 계산은 여기서 하고, 화면은 받은 값을 그대로
    보여주기만 한다(`grade_rules.py`가 붙인 규칙 그대로)."""

    def __init__(self, repository: VideoPort) -> None:
        self._repository = repository

    def __call__(self, command: GetCardGradeCommand) -> CardGradeResult:
        row = self._repository.find_card_grade(command.card_public_slug)
        if row is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")
        trust_dominant = is_trust_dominant(row.trust_positive, row.trust_total)
        return CardGradeResult(
            grade=display_grade(row.overall_grade, trust_dominant),
            provisional=row.provisional,
            notes=row.card_notes,
        )


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
        analysis_failure_reason=video.analysis_failure_reason,
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
