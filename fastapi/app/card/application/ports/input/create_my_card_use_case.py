"""입력 포트 — 내 카드 생성."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.card.application.dtos.card_dto import CreateMyCardCommand, MyCardCreation


class CreateMyCardUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CreateMyCardCommand) -> MyCardCreation:
        """카드를 만든다. **이미 있으면 그것을 돌려준다** — 멱등이다.

        만들었는지 이미 있었는지는 `MyCardCreation.created` 로 알린다. 라우터가
        201 과 200 을 가르는 데 쓴다.
        """
