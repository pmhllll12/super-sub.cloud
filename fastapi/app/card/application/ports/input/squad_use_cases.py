"""스쿼드 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.card.application.dtos.squad_dto import (
    CreateSquadCommand,
    DischargeMemberCommand,
    EnlistCardCommand,
    PublicSquadQuery,
    SquadCreation,
    SquadResult,
    TeamSquadQuery,
)


class CreateSquadUseCase(ABC):
    @abstractmethod
    def __call__(self, command: CreateSquadCommand) -> SquadCreation:
        """스쿼드를 만든다. **주장만 할 수 있고, 멱등이다.**"""


class TeamSquadUseCase(ABC):
    @abstractmethod
    def __call__(self, query: TeamSquadQuery) -> SquadResult:
        """팀 화면에서 보는 스쿼드. 소속이면 볼 수 있다."""


class PublicSquadUseCase(ABC):
    @abstractmethod
    def __call__(self, query: PublicSquadQuery) -> SquadResult:
        """공유 슬러그로 보는 스쿼드. **인증하지 않는다.**"""


class EnlistCardUseCase(ABC):
    @abstractmethod
    def __call__(self, command: EnlistCardCommand) -> SquadResult:
        """카드를 등재한다. **주장만 할 수 있다.**"""


class DischargeMemberUseCase(ABC):
    @abstractmethod
    def __call__(self, command: DischargeMemberCommand) -> SquadResult:
        """등재를 뺀다. **주장만 할 수 있다.**"""
