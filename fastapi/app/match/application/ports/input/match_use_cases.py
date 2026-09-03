"""경기 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.match.application.dtos.match_dto import (
    AcceptApplicationCommand,
    ApplicationResult,
    ApplicationsQuery,
    ApplyCommand,
    CancelMatchCommand,
    CreateMatchCommand,
    UpdateMatchCommand,
    MatchQuery,
    MatchResult,
    MatchSearchQuery,
    MatchSearchResult,
    TeamMatchesQuery,
)


class CreateMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CreateMatchCommand) -> MatchResult:
        """경기를 등록한다. **주장만 할 수 있다.**"""


class ReadMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, query: MatchQuery) -> MatchResult:
        """경기 1건. 없으면 404."""


class ListTeamMatchesUseCase(ABC):
    @abstractmethod
    def __call__(self, query: TeamMatchesQuery) -> list[MatchResult]:
        """그 팀의 다가오는 경기 목록."""


class UpdateMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, command: UpdateMatchCommand) -> MatchResult:
        """경기를 고친다. **주장만 할 수 있고, 지난 경기는 못 고친다.**"""


class CancelMatchUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CancelMatchCommand) -> None:
        """경기를 취소한다. **지원이 하나라도 붙었으면 막힌다.**"""


class SearchMatchesUseCase(ABC):
    @abstractmethod
    def __call__(self, query: MatchSearchQuery) -> MatchSearchResult:
        """종목·지역으로 다가오는 경기를 찾는다. **팀 id 를 몰라도 된다.**"""
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
