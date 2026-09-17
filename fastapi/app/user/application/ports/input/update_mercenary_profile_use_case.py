"""입력 포트 — 내 용병 프로필 수정."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.mercenary_dto import (
    MercenaryProfileResult,
    UpdateMercenaryProfileCommand,
)


class UpdateMercenaryProfileUseCase(ABC):
    @abstractmethod
    def __call__(
        self, command: UpdateMercenaryProfileCommand
    ) -> MercenaryProfileResult:
        """바뀐 뒤의 프로필 전체를 돌려준다(`UpdateMeUseCase`와 같은 관례).

        `skill_summary`가 바뀌면 임베딩을 다시 계산해 함께 저장한다 — 호출
        쪽이 별도로 "임베딩 갱신" 같은 걸 부를 필요가 없다.
        """
