"""내 카드 인터랙터."""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import MyCardQuery, MyCardResult
from app.card.application.ports.input.my_card_use_case import MyCardUseCase
from app.card.application.ports.output.card_port import CardPort
from app.card.application.use_cases.card_assembler import to_my_card_result
from app.card.domain.rules.card_rules import visible_titles
from app.core.errors import ApiError


class MyCardInteractor(MyCardUseCase):
    def __init__(self, repository: CardPort) -> None:
        self._repository = repository

    def __call__(self, query: MyCardQuery) -> MyCardResult:
        card = self._repository.find_by_owner(query.user_id)
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        card = replace(card, titles=visible_titles(card.titles))
        return to_my_card_result(card)
