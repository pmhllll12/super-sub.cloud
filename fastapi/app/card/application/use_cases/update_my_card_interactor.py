"""내 카드 수정 인터랙터."""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import UNSET, MyCardResult
from app.card.application.ports.input.update_my_card_use_case import (
    UpdateMyCardCommand,
    UpdateMyCardUseCase,
)
from app.card.application.ports.output.card_port import CardPort
from app.card.application.ports.output.photo_storage_port import PhotoStoragePort
from app.card.application.use_cases.card_assembler import photo_url_of, to_my_card_result
from app.card.domain.rules.card_rules import (
    normalize_custom_titles,
    normalize_tagline,
    owns_photo_key,
    visible_titles,
)
from app.core.errors import ApiError


class UpdateMyCardInteractor(UpdateMyCardUseCase):
    def __init__(
        self, repository: CardPort, photos: PhotoStoragePort | None = None
    ) -> None:
        self._repository = repository
        # 🔴 **없어도 된다**(로컬·시험). 그때는 사진 주소가 `None` 이고,
        #    바뀐 사진의 옛 파일을 지우지 않는다(지울 데가 없다).
        self._photos = photos

    def __call__(self, command: UpdateMyCardCommand) -> MyCardResult:
        # 🔴 **둘 다 `UNSET` 일 수 있다** — 지금은 `www` 가 안 그러지만, 계약상
        #    빈 PATCH 본문도 유효하다. 그때는 아무것도 안 바꾸고 지금 카드를
        #    그대로 돌려준다(404 판정을 위해 조회는 늘 한다).
        card = self._repository.find_by_owner(command.user_id)
        if card is None:
            # **카드를 여기서 만들지 않는다.** 만드는 자리는 `POST /me/card` 하나다
            # (3장 — "카드는 여기서만 생긴다"). 수정이 생성을 겸하면 그 규칙이
            # 두 곳으로 흩어진다.
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        if command.tagline is not UNSET:
            card = self._repository.update_tagline(
                command.user_id, normalize_tagline(command.tagline)
            )
        if command.style is not UNSET:
            """🔴 **남의 키를 내 카드에 못 붙인다.**

            키는 비밀이 아니다 — 카드 응답에 실려 나간다. 사전 서명도 키만
            알면 만들어지므로, **저장 시점에 접두사를 대조하는 것이 유일한
            방어선**이다(영상의 `owns_key` 와 같은 자리). 스키마는 길이만
            보고 권한은 안 본다 — 층이 다르다.
            """
            new_key = (command.style or {}).get("photo_key")
            if new_key and not owns_photo_key(new_key, command.user_id):
                raise ApiError(
                    422, "PHOTO_KEY_NOT_OWNED", "그 사진을 쓸 수 없습니다."
                )
            # 🔴 **바뀐 사진의 옛 파일을 지운다.** 안 지우면 버킷에 주인 없는
            #    사진이 쌓이고, 키를 아는 사람은 계속 볼 수 있다.
            old_key = (card.style or {}).get("photo_key")
            card = self._repository.update_style(command.user_id, command.style)
            if old_key and old_key != new_key and self._photos is not None:
                # 지우기가 실패해도 저장은 성공이다 — 사람이 한 일은 끝났고,
                # 남는 것은 우리 쪽 청소다(영상 삭제와 같은 판단).
                try:
                    self._photos.delete_object(old_key)
                except Exception:  # noqa: BLE001 - 청소 실패가 저장을 막으면 안 된다
                    pass
        if command.titles is not UNSET:
            # `paik` 36번. 길이·개수는 규칙이 거부한다(자르지 않는다) —
            # 스키마가 먼저 막지만 도메인에도 같은 선이 있어야 한다.
            try:
                labels = normalize_custom_titles(command.titles)
            except ValueError as exc:
                raise ApiError(422, "INVALID_TITLE", str(exc)) from exc
            card = self._repository.replace_custom_titles(command.user_id, labels)
        # `card` 는 위에서 이미 None 이 아님을 확인했다 — 사이에 지워질 동시성
        # 창은 있지만(다른 요청이 카드를 지운다는 경로가 지금 없다), 있었다면
        # 아래 두 갱신도 None 을 돌려주므로 그때 다시 확인해 준다.
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        card = replace(card, titles=visible_titles(card.titles))
        return to_my_card_result(card, photo_url_of(card.style, self._photos))
