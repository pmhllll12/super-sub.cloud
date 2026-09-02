"""팀 입력 포트 넷.

한 파일에 모았다 — 같은 자원(`team`)을 다루고 **네 개가 함께 바뀌기 때문**이다.
카드 쪽은 조회 두 개가 서로 무관해서 파일을 나눴다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.team_dto import (
    CreateTeamCommand,
    JoinTeamCommand,
    LeaveTeamCommand,
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
