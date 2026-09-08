"""영상 라우터. 계약 문서 3-5절."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.analysis.adapter.inbound.api.schemas.video_schema import (
    PlaybackUrlResponse,
    PublicVideoResponse,
    RegisterVideoSchema,
    UpdateVideoSchema,
    UploadUrlResponse,
    UploadUrlSchema,
    VideoResponse,
)
from app.analysis.application.dtos.video_dto import (
    UNSET,
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
from app.analysis.dependencies.video_providers import (
    CreateUploadUrlUseCaseDep,
    DeleteVideoUseCaseDep,
    GetPlaybackUrlUseCaseDep,
    KeepVideoUseCaseDep,
    ListMyVideosUseCaseDep,
    ListPublicVideosUseCaseDep,
    RegisterVideoUseCaseDep,
    UpdateVideoUseCaseDep,
)
from app.core.deps import CurrentUserId

video_router = APIRouter(tags=["videos"])


@video_router.post("/videos/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    body: UploadUrlSchema,
    user_id: CurrentUserId,
    use_case: CreateUploadUrlUseCaseDep,
) -> UploadUrlResult:
    """올릴 자리를 받는다. **아직 영상이 만들어지지 않는다** — 그래서 200 이다.

    받은 `upload_url` 에 PUT 한 뒤 `POST /videos` 로 등록한다.
    """
    return use_case(
        UploadUrlCommand(
            user_id=user_id,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
            filename=body.filename,
        )
    )


@video_router.post(
    "/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED
)
def register_video(
    body: RegisterVideoSchema,
    user_id: CurrentUserId,
    use_case: RegisterVideoUseCaseDep,
) -> VideoResult:
    """올린 클립을 등록하고 규격을 검사한다(SFR-001).

    🔴 **규격에 안 맞아도 201 이다.** 반려 사유를 값으로 남기는 것이 이
    엔드포인트의 목적이라, 422 로 돌려보내면 사유가 아무 데도 안 남는다.
    통과 여부는 `passed` 로 본다.
    """
    return use_case(
        RegisterVideoCommand(
            user_id=user_id,
            sport_code=body.sport_code,
            storage_key=body.storage_key,
            duration_ms=body.duration_ms,
            width=body.width,
            height=body.height,
            side=body.side,
            analyze=body.analyze,
            original_filename=body.filename,
        )
    )


@video_router.get("/videos", response_model=list[VideoResponse])
def list_my_videos(
    user_id: CurrentUserId, use_case: ListMyVideosUseCaseDep
) -> list[VideoResult]:
    """내 영상 목록. 최근 것이 앞에 온다.

    **남의 영상은 담기지 않는다** — 목록은 언제나 자기 것이다.
    """
    return use_case(MyVideosQuery(user_id=user_id))


@video_router.get("/videos/public", response_model=list[PublicVideoResponse])
def list_public_videos(
    _user_id: CurrentUserId, use_case: ListPublicVideosUseCaseDep
) -> list[PublicVideoResult]:
    """공개된 클립. 최근 것이 앞에 온다. 홈의 영상 모음이 쓴다.

    🔴 **로그인이 필요하다.** 익명 피드가 필요하면 열겠다 — 지금은 확인 방법이
    "다른 계정으로 로그인해도 보인다"라 인증을 그대로 둔다.

    저장 키·업로더는 안 실린다. 재생은 `GET /videos/{id}/playback-url` 로 받는다.
    """
    return use_case(PublicVideosQuery())


@video_router.get(
    "/videos/{video_id}/playback-url", response_model=PlaybackUrlResponse
)
def get_playback_url(
    video_id: UUID,
    user_id: CurrentUserId,
    use_case: GetPlaybackUrlUseCaseDep,
) -> PlaybackUrlResult:
    """재생용 사전 서명 GET URL.

    **공개 클립이거나 자기 클립일 때만.** 아니면 `404 VIDEO_NOT_FOUND` —
    비공개 남의 클립은 "없음"과 같게 답한다.
    """
    return use_case(
        GetPlaybackUrlCommand(video_id=video_id, user_id=user_id)
    )


@video_router.patch("/videos/{video_id}", response_model=VideoResponse)
def update_video(
    video_id: UUID,
    body: UpdateVideoSchema,
    user_id: CurrentUserId,
    use_case: UpdateVideoUseCaseDep,
) -> VideoResult:
    """클립을 부분 수정한다 — 공개 여부·제목·한 줄 설명.

    **보낸 필드만** 바뀐다. **자기 클립만.** 남의 클립이거나 없는 클립이면
    `404 VIDEO_NOT_FOUND` — 존재 여부를 구별해 주지 않는다.
    """
    sent = body.model_fields_set
    return use_case(
        UpdateVideoCommand(
            video_id=video_id,
            user_id=user_id,
            # `is_public` 은 불리언이라 `null` 은 뜻이 없다 — 보냈어도 무시한다.
            is_public=(
                body.is_public
                if "is_public" in sent and body.is_public is not None
                else UNSET
            ),
            title=body.title if "title" in sent else UNSET,
            description=body.description if "description" in sent else UNSET,
        )
    )


@video_router.post("/videos/{video_id}/keep", response_model=VideoResponse)
def keep_video(
    video_id: UUID,
    user_id: CurrentUserId,
    use_case: KeepVideoUseCaseDep,
) -> VideoResult:
    """"내 프로필에 리포트 저장" — `/analysis` 임시 분석을 영구로 만든다.

    `kept` 를 켜고, 임시 원본(`videos/…`)이면 리포트 자리
    (`reports/<user_id>/<video_id>/source.<ext>`)로 옮긴다(S3 `CopyObject`).
    **자기 클립만.** 남의/없는 클립이면 `404 VIDEO_NOT_FOUND`.

    **멱등이다** — 이미 저장된 클립에 다시 불러도 `200` 이고 이동은 건너뛴다.
    """
    return use_case(KeepVideoCommand(video_id=video_id, user_id=user_id))


@video_router.delete(
    "/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_video(
    video_id: UUID,
    user_id: CurrentUserId,
    use_case: DeleteVideoUseCaseDep,
) -> None:
    """클립을 지운다 — DB 행(판정·작업 연쇄 포함)과 S3 객체.

    **자기 클립만.** 남의 클립이거나 없는 클립이면 `404 VIDEO_NOT_FOUND`.
    S3 정리는 best-effort다 — 실패해도 `204` 이고 남은 객체는 백스톱 스윕이 잡는다.
    """
    use_case(DeleteVideoCommand(video_id=video_id, user_id=user_id))
