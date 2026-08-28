"""로그인 인터랙터."""

from __future__ import annotations

from app.core.errors import ApiError
from app.core.logging import log_auth_event
from app.core.security import TOKEN_EXPIRES_IN, issue_access_token
from app.user.application.dtos.login_dto import LoginCommand, LoginResult
from app.user.application.ports.input.login_use_case import LoginUseCase
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.password_vo import Password


class LoginInteractor(LoginUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, command: LoginCommand) -> LoginResult:
        user = self._repository.find_by_credentials(
            Email.of(command.email), Password(command.password)
        )
        if user is None:
            # 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다 —
            # 구분하면 가입 여부가 새어 나간다(계약 문서 2장).
            raise ApiError(
                401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 실패는 `ApiError` 핸들러가 한자리에서 남긴다. 성공은 여기서만 사용자 id 를
        # 알 수 있어서(응답에는 토큰뿐이다) 이 자리에 둔다.
        log_auth_event("login_success", user_id=user.id)
        return LoginResult(
            access_token=issue_access_token(user.id),
            expires_in=TOKEN_EXPIRES_IN,
        )
