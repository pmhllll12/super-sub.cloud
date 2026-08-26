"""내 정보 인터랙터."""

from __future__ import annotations

from app.core.errors import ApiError
from app.user.application.dtos.me_dto import MeQuery, MeResult
from app.user.application.use_cases.me_assembler import build_me_result
from app.user.application.ports.input.me_use_case import MeUseCase
from app.user.application.ports.output.user_port import UserPort
from app.user.domain.rules.membership_rules import active_memberships


class MeInteractor(MeUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, query: MeQuery) -> MeResult:
        user = self._repository.get(query.user_id)
        if user is None:
            # 토큰은 유효한데 사용자가 없다 — 탈퇴했거나 위조된 id 다.
            raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

        memberships = active_memberships(
            self._repository.list_memberships(query.user_id)
        )
        return build_me_result(user, memberships)
