"""비밀번호 변경 인터랙터. 5장 SEC-004.

**바꾸면 기존 토큰을 전부 끊는다.** 비밀번호를 바꾸는 이유는 대개 "누가 내 계정을
쓰고 있는 것 같다"이고, 그때 옛 토큰이 7일 더 살아 있으면 바꾼 의미가 없다.

현재 비밀번호를 함께 받는 이유는 반대 방향의 사고를 막기 위해서다 — 토큰만으로
바꿀 수 있으면, **토큰을 훔친 쪽이 비밀번호를 갈아 주인을 밀어낼 수 있다.**
"""

from __future__ import annotations

from app.core.errors import ApiError
from app.core.logging import log_auth_event
from app.user.application.dtos.me_dto import ChangePasswordCommand
from app.user.application.ports.input.change_password_use_case import (
    ChangePasswordUseCase,
)
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.value_objects.password_vo import Password


class ChangePasswordInteractor(ChangePasswordUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: ChangePasswordCommand) -> None:
        user = self._repository.get(command.user_id)
        if user is None:
            raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

        # 재인증. 자격증명 확인은 저장소가 하므로 해시 방식을 여기서 알 필요가 없다.
        verified = self._repository.find_by_credentials(
            user.email, Password(command.current_password)
        )
        if verified is None:
            # 로그인 실패와 **같은 code** 를 쓴다. 여기만 다른 code 를 주면
            # 클라이언트가 분기를 하나 더 들어야 한다.
            raise ApiError(
                401, "INVALID_CREDENTIALS", "현재 비밀번호가 올바르지 않습니다."
            )

        self._repository.change_password(user.id, Password(command.new_password))
        # 🔴 순서가 중요하다. 바꾼 **뒤에** 끊는다 — 먼저 끊고 변경이 실패하면
        #    옛 비밀번호는 그대로인데 로그인만 풀린 상태가 된다.
        self._repository.bump_token_version(user.id)
        log_auth_event("password_changed", user_id=user.id)
