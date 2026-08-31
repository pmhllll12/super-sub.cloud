"""입력 포트 — 회원 강제 탈퇴(관리자)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.user.application.dtos.admin_dto import ForceDeleteUserCommand


class ForceDeleteUserUseCase(ABC):
    @abstractmethod
    def __call__(self, command: ForceDeleteUserCommand) -> None:
        """비밀번호 확인 없이 계정을 지운다. 관리자 인증은 라우터 게이트가 이미 확인했다."""
