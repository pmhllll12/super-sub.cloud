"""경기 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.match.application.dtos.match_dto import (
    CreateMatchCommand,
    MatchQuery,
    MatchResult,
)


class CreateMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CreateMatchCommand) -> MatchResult:
        """경기를 등록한다. **주장만 할 수 있다.**"""


class ReadMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, query: MatchQuery) -> MatchResult:
        """경기 1건. 없으면 404."""
