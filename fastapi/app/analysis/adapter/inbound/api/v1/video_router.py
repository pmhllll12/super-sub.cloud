"""영상 라우터. 계약 문서 3-5절."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.analysis.adapter.inbound.api.schemas.video_schema import (
    RegisterVideoSchema,
    UploadUrlResponse,
    UploadUrlSchema,
    VideoResponse,
)
from app.analysis.application.dtos.video_dto import (
    MyVideosQuery,
    RegisterVideoCommand,
    UploadUrlCommand,
    UploadUrlResult,
    VideoResult,
)
from app.analysis.dependencies.video_providers import (
    CreateUploadUrlUseCaseDep,
    ListMyVideosUseCaseDep,
    RegisterVideoUseCaseDep,
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
