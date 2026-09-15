"""분석 작업 입력 포트. `Claim`·`Finish`는 워커 전용, `Request`·`GetDetectionStatus`는
사람(화면)이 부른다 — 미결 `ho` 44번.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.application.dtos.job_dto import (
    ClaimedJobResult,
    DetectionStatusQuery,
    DetectionStatusResult,
    FinishJobCommand,
    RequestDetectionCommand,
)


class ClaimJobUseCase(ABC):
    @abstractmethod
    def __call__(self) -> ClaimedJobResult | None:
        """큐에서 하나 집는다. 없으면 None — **오류가 아니다.**"""


class FinishJobUseCase(ABC):
    @abstractmethod
    def __call__(self, command: FinishJobCommand) -> None:
        """집었던 작업을 끝낸다."""


class RequestDetectionUseCase(ABC):
    @abstractmethod
    def __call__(self, command: RequestDetectionCommand) -> DetectionStatusResult:
        """`detect` 작업을 큐에 넣는다. 호출마다 새 작업(재사용 안 함)."""


class GetDetectionStatusUseCase(ABC):
    @abstractmethod
    def __call__(self, query: DetectionStatusQuery) -> DetectionStatusResult:
        """그 영상의 가장 최근 `detect` 작업 상태를 본다."""
