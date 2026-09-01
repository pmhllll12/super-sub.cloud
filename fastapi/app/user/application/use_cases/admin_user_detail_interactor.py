"""회원 상세(관리자) 인터랙터."""

from __future__ import annotations

from app.core.errors import ApiError
from app.user.application.dtos.admin_dto import (
    AdminMembershipResult,
    AdminUserDetailQuery,
    AdminUserDetailResult,
)
from app.user.application.ports.input.admin_user_detail_use_case import (
    AdminUserDetailUseCase,
)
from app.user.application.ports.output.user_port import UserPort


class AdminUserDetailInteractor(AdminUserDetailUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, query: AdminUserDetailQuery) -> AdminUserDetailResult:
        user = self._repository.get(query.user_id)
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "회원을 찾을 수 없습니다.")

        # `MeInteractor` 와 달리 나간 팀을 거르지 않는다 — 관리자는 이력 전체를 본다.
        memberships = self._repository.list_memberships(query.user_id)
        has_card = self._repository.has_card(query.user_id)

        return AdminUserDetailResult(
            id=user.id,
            email=str(user.email),
            nickname=str(user.nickname),
            created_at=user.created_at,
            teams=[
                AdminMembershipResult(
                    team_id=m.team_id,
                    name=m.name,
                    region=m.region,
                    sport_code=m.sport_code,
                    role=m.role,
                    joined_at=m.joined_at,
                    left_at=m.left_at,
                )
                for m in memberships
            ],
            has_card=has_card,
        )
