"""카드 사진 업로드 인터랙터 (2026-09-18, 사용자 요청).

🔴 **바이트가 앱 서버를 지나지 않는다**(PER-002). 사전 서명 PUT 주소만 만들고,
올리는 것은 브라우저가 S3 에 직접 한다 — 영상과 같은 방식이다.
"""

from __future__ import annotations

from app.card.application.dtos.card_dto import (
    CardPhotoUploadCommand,
    CardPhotoUploadResult,
)
from app.card.application.ports.input.card_photo_use_case import CardPhotoUploadUseCase
from app.card.application.ports.output.card_port import CardPort
from app.card.application.ports.output.photo_storage_port import PhotoStoragePort
from app.card.domain.rules.card_rules import build_photo_key, extension_for_content_type
from app.core.errors import ApiError


class CardPhotoUploadInteractor(CardPhotoUploadUseCase):
    def __init__(self, repository: CardPort, photos: PhotoStoragePort) -> None:
        self._repository = repository
        self._photos = photos

    def __call__(self, command: CardPhotoUploadCommand) -> CardPhotoUploadResult:
        """🔴 **카드가 먼저 있어야 한다** — 키에 카드 id 가 들어가고, 사진은
        카드에 붙는 것이라 카드 없이 올릴 자리를 내줄 이유가 없다."""
        card = self._repository.find_by_owner(command.user_id)
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        extension = extension_for_content_type(command.content_type)
        if extension is None:
            # 🔴 **여기서 막지 않으면 우리 버킷에 `.html` 이 올라간다.** 사전
            #    서명 PUT 은 내용을 검사하지 않는다. `image/svg+xml` 도 막는다 —
            #    SVG 는 스크립트를 담을 수 있다.
            raise ApiError(
                422,
                "UNSUPPORTED_PHOTO_TYPE",
                "사진으로 올릴 수 없는 형식입니다.",
            )

        key = build_photo_key(command.user_id, card.id, extension)
        url, expires_in = self._photos.create_upload_url(key, command.content_type)
        return CardPhotoUploadResult(
            upload_url=url, storage_key=key, expires_in=expires_in
        )
