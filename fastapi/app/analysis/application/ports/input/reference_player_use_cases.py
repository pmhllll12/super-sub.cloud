"""선수 목록·관절 결과 입력 포트. `paik` 29번."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.application.dtos.reference_player_dto import (
    GetReferencePlayerSkeletonQuery,
    GetVideoSkeletonQuery,
    ListReferencePlayersQuery,
    ReferencePlayerResult,
    SkeletonResult,
)


class ListReferencePlayersUseCase(ABC):
    @abstractmethod
    def __call__(
        self, query: ListReferencePlayersQuery
    ) -> list[ReferencePlayerResult]:
        """전체 선수 목록."""


class GetReferencePlayerSkeletonUseCase(ABC):
    @abstractmethod
    def __call__(self, query: GetReferencePlayerSkeletonQuery) -> SkeletonResult:
        """그 선수 리포트의 `skeleton` 그대로. 선수가 없으면 404(`ApiError`)."""


class GetVideoSkeletonUseCase(ABC):
    @abstractmethod
    def __call__(self, query: GetVideoSkeletonQuery) -> SkeletonResult:
        """내 영상의 `skeleton` 그대로. 영상이 없거나 남의 것·분석 미완료·
        분석 실패면 404(`ApiError`, `ReadReportInteractor`와 같은 코드 셋).
        """
