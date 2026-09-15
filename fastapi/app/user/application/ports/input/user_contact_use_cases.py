"""지인 신청·검색 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.user_contact_dto import (
    AcceptContactCommand,
    ContactListResult,
    ContactResult,
    ListContactRequestsQuery,
    ListContactsQuery,
    RequestContactCommand,
    SearchUsersQuery,
    UserSearchResult,
)


class SearchUsersUseCase(ABC):
    @abstractmethod
    def __call__(self, query: SearchUsersQuery) -> list[UserSearchResult]:
        """닉네임으로 사용자를 찾는다. 지인 신청 전 상대를 찾는 자리."""


class RequestContactUseCase(ABC):
    @abstractmethod
    def __call__(self, command: RequestContactCommand) -> ContactResult:
        """지인 신청을 보낸다. 대상에게 알림이 간다."""


class AcceptContactUseCase(ABC):
    @abstractmethod
    def __call__(self, command: AcceptContactCommand) -> ContactResult:
        """대상이 신청을 수락한다. 신청자에게 알림이 간다."""


class ListContactsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListContactsQuery) -> ContactListResult:
        """수락된 지인 목록."""


class ListContactRequestsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListContactRequestsQuery) -> list[ContactResult]:
        """나에게 온, 아직 수락 안 한 신청 목록."""
