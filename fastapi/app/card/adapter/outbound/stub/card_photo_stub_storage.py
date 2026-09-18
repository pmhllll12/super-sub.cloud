"""`PhotoStoragePort` 의 시험용 구현 — S3 없이 계약 시험이 돌게 한다.

포트를 둔 이유가 **갈아끼우기가 아니라 검사**라는 것이 여기서 드러난다
(`analysis` 의 같은 자리와 같은 판단).
"""

from __future__ import annotations

from app.card.application.ports.output.photo_storage_port import PhotoStoragePort

_TTL = 900


class CardPhotoStubStorage(PhotoStoragePort):
    def __init__(self) -> None:
        # 지운 키를 시험이 확인할 수 있게 남긴다.
        self.deleted: list[str] = []

    def create_upload_url(self, storage_key: str, content_type: str) -> tuple[str, int]:
        return f"https://stub.invalid/put/{storage_key}?ct={content_type}", _TTL

    def create_download_url(self, storage_key: str) -> tuple[str, int]:
        return f"https://stub.invalid/get/{storage_key}", _TTL

    def delete_object(self, storage_key: str) -> None:
        self.deleted.append(storage_key)
