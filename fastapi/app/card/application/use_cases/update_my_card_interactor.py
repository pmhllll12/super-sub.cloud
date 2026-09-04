"""내 카드 수정 인터랙터."""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import MyCardResult
from app.card.application.ports.input.update_my_card_use_case import (
    UpdateMyCardCommand,
    UpdateMyCardUseCase,
)
from app.card.application.ports.output.card_port import CardPort
from app.card.application.use_cases.card_assembler import to_my_card_result
from app.card.domain.rules.card_rules import normalize_tagline, visible_titles
from app.core.errors import ApiError


class UpdateMyCardInteractor(UpdateMyCardUseCase):
    def __init__(self, repository: CardPort) -> None:
        self._repository = repository

    def __call__(self, command: UpdateMyCardCommand) -> MyCardResult:
        card = self._repository.update_tagline(
            command.user_id, normalize_tagline(command.tagline)
        )
        if card is None:
            # **카드를 여기서 만들지 않는다.** 만드는 자리는 `POST /me/card` 하나다
            # (3장 — "카드는 여기서만 생긴다"). 수정이 생성을 겸하면 그 규칙이
            # 두 곳으로 흩어진다.
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        card = replace(card, titles=visible_titles(card.titles))
        return to_my_card_result(card)
