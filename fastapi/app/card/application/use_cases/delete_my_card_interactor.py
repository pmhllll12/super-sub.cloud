"""내 카드 지우기 인터랙터 (2026-09-19, 미결 `paik` — 카드 「초기화」).

카드가 생기는 자리가 `POST /me/card` 하나이듯, 없어지는 자리도 여기 하나다.
화면의 「초기화」가 이것을 불러 **카드를 안 만든 처음 상태**로 돌아간다(사용자 요청).
"""

from __future__ import annotations

from app.card.application.dtos.card_dto import DeleteMyCardCommand
from app.card.application.ports.input.delete_my_card_use_case import (
    DeleteMyCardUseCase,
)
from app.card.application.ports.output.card_port import CardPort


class DeleteMyCardInteractor(DeleteMyCardUseCase):
    def __init__(self, repository: CardPort) -> None:
        self._repository = repository

    def __call__(self, command: DeleteMyCardCommand) -> None:
        self._repository.delete_by_owner(command.user_id)
