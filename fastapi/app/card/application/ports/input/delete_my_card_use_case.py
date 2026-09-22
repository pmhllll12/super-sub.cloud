"""입력 포트 — 내 카드 지우기 (2026-09-19)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.card.application.dtos.card_dto import DeleteMyCardCommand


class DeleteMyCardUseCase(ABC):
    @abstractmethod
    def __call__(self, command: DeleteMyCardCommand) -> None:
        """카드를 지운다. **원래 없었어도 조용히 끝난다** — 멱등이다.

        지우는 요청이 네트워크에서 끊겨 다시 보내졌을 때 두 번째가 오류로 오면
        화면은 「못 지웠다」고 잘못 알린다. 결과(카드가 없다)는 같으므로 가르지
        않는다.
        """
