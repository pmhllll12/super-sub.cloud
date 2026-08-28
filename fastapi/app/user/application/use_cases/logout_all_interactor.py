"""모든 기기에서 로그아웃 — 토큰 폐기(SEC-004).

**액세스 토큰은 서명만으로 검증되므로 서버가 "잊는" 방법이 없다.** 그래서 사용자
쪽에 버전을 하나 두고, 그 값을 올려 **이전에 발급된 토큰 전부를 한 번에 무효**로
만든다. 리프레시 토큰 회전을 도입하지 않은 이유는 우리에게 필요한 것이 갱신이
아니라 폐기 능력 하나뿐이어서다.

지금은 이 유스케이스가 유일한 폐기 경로다. **비밀번호 변경과 탈퇴가 생기면 같은
포트를 부르면 된다** — 그때 폐기 로직을 새로 만들 필요가 없다.
"""

from __future__ import annotations

from uuid import UUID

from app.core.errors import ApiError
from app.core.logging import log_auth_event
from app.user.application.ports.input.logout_all_use_case import LogoutAllUseCase
from app.user.application.ports.output.user_port import UserPort


class LogoutAllInteractor(LogoutAllUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, user_id: UUID) -> None:
        user = self._repository.get(user_id)
        if user is None:
            # 토큰은 유효한데 사용자가 없다. 다른 인증 필요 경로와 같은 판단이어야
            # 클라이언트 동작이 갈리지 않는다.
            raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

        self._repository.bump_token_version(user_id)
        # 사후 추적 대상이다 — 남의 계정을 끊는 것도 이 경로를 지난다(SEC-010).
        log_auth_event("logout_all", user_id=user_id)
