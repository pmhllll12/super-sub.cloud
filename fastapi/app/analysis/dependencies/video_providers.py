"""영상 저장소·객체 저장소·유스케이스 프로바이더."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.pg.video_pg_repository import VideoPgRepository
from app.analysis.adapter.outbound.s3.s3_storage import S3Storage
from app.analysis.application.ports.input.video_use_cases import (
    CreateUploadUrlUseCase,
    ListMyVideosUseCase,
    RegisterVideoUseCase,
)
from app.analysis.application.ports.output.storage_port import StoragePort
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.application.use_cases.video_interactors import (
    CreateUploadUrlInteractor,
    ListMyVideosInteractor,
    RegisterVideoInteractor,
)
from app.core.config import settings
from app.core.database import get_session
from app.core.errors import ApiError


def get_video_repository(
    session: Annotated[Session, Depends(get_session)],
) -> VideoPort:
    return VideoPgRepository(session)


VideoRepositoryDep = Annotated[VideoPort, Depends(get_video_repository)]


def get_storage() -> StoragePort:
    """객체 저장소.

    🔴 **버킷이 없으면 503 이다.** `JWT_SECRET` 과 같은 판단이다 — 조용한
    기본값(로컬 디렉터리 등)을 두면 배포에 설정을 안 넣었을 때 파일이 엉뚱한
    곳에 쌓이고, 그것을 알아차리는 시점은 원본이 필요해진 뒤다.
    """
    if not settings.s3_bucket:
        raise ApiError(
            503, "STORAGE_NOT_CONFIGURED", "저장소가 설정되지 않았습니다."
        )
    return S3Storage(
        bucket=settings.s3_bucket,
        region=settings.aws_region,
        url_ttl_seconds=settings.upload_url_ttl_seconds,
    )


StorageDep = Annotated[StoragePort, Depends(get_storage)]


def get_create_upload_url_use_case(storage: StorageDep) -> CreateUploadUrlUseCase:
    return CreateUploadUrlInteractor(storage)


def get_register_video_use_case(
    repository: VideoRepositoryDep, storage: StorageDep
) -> RegisterVideoUseCase:
    return RegisterVideoInteractor(repository, storage)


def get_list_my_videos_use_case(
    repository: VideoRepositoryDep,
) -> ListMyVideosUseCase:
    return ListMyVideosInteractor(repository)


CreateUploadUrlUseCaseDep = Annotated[
    CreateUploadUrlUseCase, Depends(get_create_upload_url_use_case)
]
RegisterVideoUseCaseDep = Annotated[
    RegisterVideoUseCase, Depends(get_register_video_use_case)
]
ListMyVideosUseCaseDep = Annotated[
    ListMyVideosUseCase, Depends(get_list_my_videos_use_case)
]
