"""입력 포트 — 용병 후보 검색."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.mercenary_dto import (
    CandidateResult,
    SearchCandidatesQuery,
)


class SearchCandidatesUseCase(ABC):
    @abstractmethod
    def __call__(self, query: SearchCandidatesQuery) -> list[CandidateResult]:
        """유사도 내림차순. 결과가 없으면 빈 리스트(에러 아님)."""
