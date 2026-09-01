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
        # 자기 자신은 이 경로로 지우지 않는다. 관리자가 스스로를 지우면 지운 사람이
        # 사라져 감사 기록의 상대가 없어지고, 되돌릴 방법도 없다. 본인 탈퇴는
        # 비밀번호를 확인하는 `DELETE /me` 가 맡는다.
        if command.admin_id == command.user_id:
            raise ApiError(
                409, "CANNOT_DELETE_SELF", "자기 자신은 강제 탈퇴시킬 수 없습니다."
            )

        user = self._repository.get(command.user_id)
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "회원을 찾을 수 없습니다.")

        # `DeleteMeInteractor` 와 달리 비밀번호를 확인하지 않는다 — 관리자 인증은
        # 라우터의 `require_admin` 게이트가 이미 확인했다. 그래서 **누가 눌렀는지**를
        # 남기는 것이 여기서는 더 중요하다 (SEC-010).
        log_auth_event("admin_force_delete", admin_id=command.admin_id, user_id=user.id)
        self._repository.delete(command.user_id)
