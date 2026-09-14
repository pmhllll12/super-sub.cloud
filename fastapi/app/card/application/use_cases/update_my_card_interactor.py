"""내 카드 수정 인터랙터."""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import UNSET, MyCardResult
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
            card = self._repository.update_style(command.user_id, command.style)
        # `card` 는 위에서 이미 None 이 아님을 확인했다 — 사이에 지워질 동시성
        # 창은 있지만(다른 요청이 카드를 지운다는 경로가 지금 없다), 있었다면
        # 아래 두 갱신도 None 을 돌려주므로 그때 다시 확인해 준다.
        if card is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        card = replace(card, titles=visible_titles(card.titles))
        return to_my_card_result(card)
