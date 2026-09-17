"""경기 조건·후보 입력 포트. `paik` 18·20·21번."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.match.application.dtos.match_preference_dto import (
    GetMemberPreferenceQuery,
    GetTeamPreferenceQuery,
    ListMatchCandidatesQuery,
    ListMemberPreferencesQuery,
    ListSquadCandidatesQuery,
    MatchCandidateResult,
    MemberPreferenceResult,
    MemberPreferenceSummaryResult,
    SetMemberPreferenceCommand,
    SetTeamPreferenceCommand,
    SquadCandidateResult,
    TeamPreferenceResult,
)


class SetTeamPreferenceUseCase(ABC):
    @abstractmethod
    def __call__(self, command: SetTeamPreferenceCommand) -> TeamPreferenceResult: ...


class GetTeamPreferenceUseCase(ABC):
    @abstractmethod
    def __call__(self, query: GetTeamPreferenceQuery) -> TeamPreferenceResult: ...


class SetMemberPreferenceUseCase(ABC):
    @abstractmethod
    def __call__(
        self, command: SetMemberPreferenceCommand
    ) -> MemberPreferenceResult: ...


class GetMemberPreferenceUseCase(ABC):
    @abstractmethod
    def __call__(self, query: GetMemberPreferenceQuery) -> MemberPreferenceResult: ...


class ListMemberPreferencesUseCase(ABC):
    @abstractmethod
    def __call__(
        self, query: ListMemberPreferencesQuery
    ) -> list[MemberPreferenceSummaryResult]: ...


class ListMatchCandidatesUseCase(ABC):
    @abstractmethod
    def __call__(
        self, query: ListMatchCandidatesQuery
    ) -> list[MatchCandidateResult]: ...


class ListSquadCandidatesUseCase(ABC):
    @abstractmethod
    def __call__(
        self, query: ListSquadCandidatesQuery
    ) -> list[SquadCandidateResult]: ...
