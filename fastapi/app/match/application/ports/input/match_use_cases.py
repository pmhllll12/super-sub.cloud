"""경기 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.match.application.dtos.match_dto import (
    AcceptApplicationCommand,
    ApplicationResult,
    ApplicationsQuery,
    ApplyCommand,
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
class ApplyToMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, command: ApplyCommand) -> ApplicationResult:
        """지원하거나(본인) 제안한다(주장)."""


class AcceptApplicationUseCase(ABC):
    @abstractmethod
    def __call__(self, command: AcceptApplicationCommand) -> ApplicationResult:
        """반대쪽이 수락한다. **둘 다 차면 확정이다.**"""


class ListApplicationsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ApplicationsQuery) -> list[ApplicationResult]:
        """주장은 전부, 그 외에는 자기 건만 본다."""
