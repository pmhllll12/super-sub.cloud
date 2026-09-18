"""내 카드 인터랙터."""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import MyCardQuery, MyCardResult
from app.card.application.ports.input.my_card_use_case import MyCardUseCase
from app.card.application.ports.output.card_port import CardPort
from app.card.application.ports.output.photo_storage_port import PhotoStoragePort
from app.card.application.use_cases.card_assembler import photo_url_of, to_my_card_result
from app.card.domain.rules.card_rules import visible_titles
from app.core.errors import ApiError


class MyCardInteractor(MyCardUseCase):
    def __init__(
        self, repository: CardPort, photos: PhotoStoragePort | None = None
    ) -> None:
        self._repository = repository
        # 🔴 **없어도 된다**(로컬·시험). 그때는 사진 주소가 `None` 이다.
        self._photos = photos

    def __call__(self, query: MyCardQuery) -> MyCardResult:
        card = self._repository.find_by_owner(query.user_id)
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        card = replace(card, titles=visible_titles(card.titles))
        return to_my_card_result(card, photo_url_of(card.style, self._photos))
