"""회원 강제 탈퇴(관리자) 인터랙터."""

from __future__ import annotations

from app.core.errors import ApiError
from app.core.logging import log_auth_event
from app.user.application.dtos.admin_dto import ForceDeleteUserCommand
from app.user.application.ports.input.force_delete_user_use_case import (
    ForceDeleteUserUseCase,
)
from app.user.application.ports.output.user_port import UserPort


class ForceDeleteUserInteractor(ForceDeleteUserUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: ForceDeleteUserCommand) -> None:
        user = self._repository.get(command.user_id)
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "회원을 찾을 수 없습니다.")

        # `DeleteMeInteractor` 와 달리 비밀번호를 확인하지 않는다 — 관리자 인증은
        # 라우터의 `require_admin` 게이트가 이미 확인했다. 대신 감사 로그에
        # 누가 지웠는지는 남지 않는다(admin id 는 아직 로그 스키마에 없다) — SEC-010
        # 관점에서 이 정도로 부족하면 다음 개선 대상이다.
        log_auth_event("admin_force_delete", user_id=user.id)
        self._repository.delete(command.user_id)
