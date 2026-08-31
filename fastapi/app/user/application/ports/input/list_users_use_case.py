"""입력 포트 — 회원 목록(관리자)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.admin_dto import ListUsersQuery, ListUsersResult


class ListUsersUseCase(ABC):
    @abstractmethod
    def __call__(self, query: ListUsersQuery) -> ListUsersResult:
        """검색어로 거른 회원 목록 한 페이지와 전체 건수를 돌려준다."""
