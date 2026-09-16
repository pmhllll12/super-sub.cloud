"""팀 입력 포트 넷.

한 파일에 모았다 — 같은 자원(`team`)을 다루고 **네 개가 함께 바뀌기 때문**이다.
카드 쪽은 조회 두 개가 서로 무관해서 파일을 나눴다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.team_dto import (
    CancelTeamInvitationCommand,
    CreateTeamCommand,
    CreateTeamInvitationCommand,
    JoinTeamCommand,
    LeaveTeamCommand,
    MyTeamInvitationsQuery,
    RespondTeamInvitationCommand,
    TeamInvitationResult,
    TeamInvitationsQuery,
    TeamQuery,
    TeamResult,
)


class CreateTeamUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CreateTeamCommand) -> TeamResult:
        """팀을 만든다. **만든 사람이 `owner` 로 함께 들어간다.**"""


class ReadTeamUseCase(ABC):
    @abstractmethod
    def __call__(self, query: TeamQuery) -> TeamResult:
        """팀과 현재 구성원. 없으면 404."""


class JoinTeamUseCase(ABC):
    @abstractmethod
    def __call__(self, command: JoinTeamCommand) -> TeamResult:
        """가입하거나(본인) 남을 넣는다(`owner`)."""


class LeaveTeamUseCase(ABC):
    @abstractmethod
    def __call__(self, command: LeaveTeamCommand) -> None:
        """탈퇴하거나(본인) 남을 뺀다(`owner`). 행은 지우지 않는다."""


class CreateTeamInvitationUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CreateTeamInvitationCommand) -> TeamInvitationResult:
        """팀 주장이 개인을 초대한다(`min` 20번). 그 사람에게 알림이 간다."""


class ListTeamInvitationsUseCase(ABC):
    @abstractmethod
    def __call__(self, query: TeamInvitationsQuery) -> list[TeamInvitationResult]:
        """그 팀이 보낸 초대 목록. **주장만** 본다."""


class ListMyTeamInvitationsUseCase(ABC):
    @abstractmethod
    def __call__(
        self, query: MyTeamInvitationsQuery
    ) -> list[TeamInvitationResult]:
        """내가 받은, 아직 답 안 한 초대 목록."""


class AcceptTeamInvitationUseCase(ABC):
    @abstractmethod
    def __call__(
        self, command: RespondTeamInvitationCommand
    ) -> TeamInvitationResult:
        """받은 사람이 수락한다 — `team_member`가 새로 생긴다."""


class RejectTeamInvitationUseCase(ABC):
    @abstractmethod
    def __call__(
        self, command: RespondTeamInvitationCommand
    ) -> TeamInvitationResult:
        """받은 사람이 거절한다."""


class CancelTeamInvitationUseCase(ABC):
    @abstractmethod
    def __call__(
        self, command: CancelTeamInvitationCommand
    ) -> TeamInvitationResult:
        """보낸 팀 주장이 스스로 무른다. **아직 `pending`일 때만.**"""
