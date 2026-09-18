"""카드 사진 저장소 프로바이더 (2026-09-18).

`analysis` 의 `get_storage`·`get_storage_optional` 과 **같은 두 갈래**다 —
쓰는 자리의 성격이 다르기 때문이지 취향이 아니다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.card.adapter.outbound.s3.card_photo_s3_storage import CardPhotoS3Storage
from app.card.application.ports.output.photo_storage_port import PhotoStoragePort
from app.core.config import settings
from app.core.errors import ApiError


def _build() -> CardPhotoS3Storage:
    return CardPhotoS3Storage(
        bucket=settings.s3_bucket,
        region=settings.aws_region,
        url_ttl_seconds=settings.upload_url_ttl_seconds,
    )


def get_card_photo_storage() -> PhotoStoragePort:
    """🔴 **버킷이 없으면 503 이다.** 올릴 자리를 내주는 경로에서 쓴다 —
    조용한 기본값을 두면 설정을 빠뜨렸을 때 사진이 엉뚱한 곳에 쌓이고,
    알아차리는 시점은 카드가 안 그려진 뒤다(영상 쪽과 같은 판단).
    """
    if not settings.s3_bucket:
        raise ApiError(503, "STORAGE_NOT_CONFIGURED", "저장소가 설정되지 않았습니다.")
    return _build()


def get_card_photo_storage_optional() -> PhotoStoragePort | None:
    """버킷이 없으면 `None`. **503 을 내지 않는다.**

    🔴 **카드를 읽는 자리에서 쓴다.** 저장소 설정이 없다고 카드가 통째로
    안 열리면 안 된다 — 그때는 사진 주소만 `None` 이고 화면은 기본 장식
    그림을 그린다.
    """
    if not settings.s3_bucket:
        return None
    return _build()


CardPhotoStorageDep = Annotated[PhotoStoragePort, Depends(get_card_photo_storage)]
CardPhotoStorageOptionalDep = Annotated[
    PhotoStoragePort | None, Depends(get_card_photo_storage_optional)
]
