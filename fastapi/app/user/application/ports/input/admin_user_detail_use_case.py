"""입력 포트 — 회원 상세(관리자)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.admin_dto import AdminUserDetailQuery, AdminUserDetailResult


class AdminUserDetailUseCase(ABC):
    @abstractmethod
    def __call__(self, query: AdminUserDetailQuery) -> AdminUserDetailResult:
        """회원 정보와 소속 이력(나간 팀 포함), 카드 등록 여부를 돌려준다."""
