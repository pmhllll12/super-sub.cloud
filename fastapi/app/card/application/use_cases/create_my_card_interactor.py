"""내 카드 생성 인터랙터.

카드가 생기는 시점은 **사용자가 요청할 때**다(2026-09-02 결정, 계약 문서 3장).
가입 시 자동 생성이 아니다 — 공개 링크가 생기는 것은 사용자의 행위여야 하고,
`user` 컨텍스트가 `card` 를 임포트할 수도 없다(`tests/test_architecture.py`).
"""

from __future__ import annotations

from dataclasses import replace

from app.card.application.dtos.card_dto import CreateMyCardCommand, MyCardCreation
from app.card.application.ports.input.create_my_card_use_case import (
    CreateMyCardUseCase,
)
from app.card.application.ports.output.card_port import CardPort
from app.card.application.use_cases.card_assembler import to_my_card_result
from app.card.domain.rules.card_rules import visible_titles


class CreateMyCardInteractor(CreateMyCardUseCase):
    def __init__(self, repository: CardPort) -> None:
        self._repository = repository

    def __call__(self, command: CreateMyCardCommand) -> MyCardCreation:
        existing = self._repository.find_by_owner(command.user_id)
        if existing is not None:
            return self._result(existing, created=False)

        # 여기와 저장 사이에 남의 요청이 끼어들 수 있다. 그때는 저장소가
        # 유일 제약에 걸린 뒤 이미 있는 카드를 돌려준다 — 그래서 이 조회는
        # 최적화이지 방어선이 아니다. 방어선은 DB 의 제약이다.
        return self._result(self._repository.create_for_owner(command.user_id), True)

    def _result(self, card, created: bool) -> MyCardCreation:
        card = replace(card, titles=visible_titles(card.titles))
        return MyCardCreation(card=to_my_card_result(card), created=created)
