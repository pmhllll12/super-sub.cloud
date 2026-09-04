"""분석 작업 입력 포트. 워커 전용이다."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.application.dtos.job_dto import ClaimedJobResult, FinishJobCommand


class ClaimJobUseCase(ABC):
    @abstractmethod
    def __call__(self) -> ClaimedJobResult | None:
        """큐에서 하나 집는다. 없으면 None — **오류가 아니다.**"""


class FinishJobUseCase(ABC):
    @abstractmethod
    def __call__(self, command: FinishJobCommand) -> None:
        """집었던 작업을 끝낸다."""
