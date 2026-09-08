"""영상 라우터. 계약 문서 3-5절."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.analysis.adapter.inbound.api.schemas.video_schema import (
    PublicVideoResponse,
    RegisterVideoSchema,
    SetVisibilitySchema,
    UploadUrlResponse,
    UploadUrlSchema,
    VideoResponse,
)
from app.analysis.application.dtos.video_dto import (
    MyVideosQuery,
    PublicVideoResult,
    PublicVideosQuery,
    RegisterVideoCommand,
    SetVisibilityCommand,
    UploadUrlCommand,
    UploadUrlResult,
    VideoResult,
)
from app.analysis.dependencies.video_providers import (
    CreateUploadUrlUseCaseDep,
    ListMyVideosUseCaseDep,
    ListPublicVideosUseCaseDep,
    RegisterVideoUseCaseDep,
    SetVideoVisibilityUseCaseDep,
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

    저장 키·업로더·재생 주소는 안 실린다(미결 `paik` 5번의 3·4 조각).
    """
    return use_case(PublicVideosQuery())


@video_router.patch("/videos/{video_id}", response_model=VideoResponse)
def set_video_visibility(
    video_id: UUID,
    body: SetVisibilitySchema,
    user_id: CurrentUserId,
    use_case: SetVideoVisibilityUseCaseDep,
) -> VideoResult:
    """클립의 공개 여부를 바꾼다.

    **자기 클립만.** 남의 클립이거나 없는 클립이면 `404 VIDEO_NOT_FOUND` —
    존재 여부를 구별해 주지 않는다.
    """
    return use_case(
        SetVisibilityCommand(
            video_id=video_id, user_id=user_id, is_public=body.is_public
        )
    )
