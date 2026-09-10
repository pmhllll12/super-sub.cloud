"""입력 포트 — 내 용병 프로필 조회."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.mercenary_dto import (
    GetMercenaryProfileQuery,
    MercenaryProfileResult,
)


class GetMercenaryProfileUseCase(ABC):
    @abstractmethod
    def __call__(self, query: GetMercenaryProfileQuery) -> MercenaryProfileResult:
        """아직 한 번도 안 채웠으면 전부 기본값인 빈 프로필을 돌려준다(정상 상태)."""
