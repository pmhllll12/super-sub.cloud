"""포지션 조회 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.domain.entities.position_entity import PositionEntity


class PositionPort(ABC):
    @abstractmethod
    def sport_exists(self, sport_code: str) -> bool:
        """`sport` 에 그 코드가 있는가. 오타를 빈 목록과 가르는 데 쓴다."""

    @abstractmethod
    def list_positions(self, sport_code: str | None) -> list[PositionEntity]:
        """`sport_code` 가 있으면 그 종목만, 없으면 전 종목. `(sport_code, code)` 순."""
