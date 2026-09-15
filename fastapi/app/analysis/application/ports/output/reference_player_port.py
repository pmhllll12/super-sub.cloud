"""선수 참조 데이터 출력 포트. `paik` 29번."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.domain.entities.reference_player_entity import (
    ReferencePlayerEntity,
)


class ReferencePlayerPort(ABC):
    @abstractmethod
    def list_players(self) -> list[ReferencePlayerEntity]:
        """전체 선수 목록. 이름순."""

    @abstractmethod
    def find_player(self, player_id: str) -> ReferencePlayerEntity | None:
        """없으면 None."""
