"""회원 목록(관리자) 인터랙터."""

from __future__ import annotations

from app.user.application.dtos.admin_dto import (
    AdminUserSummary,
    ListUsersQuery,
    ListUsersResult,
)
from app.user.application.ports.input.list_users_use_case import ListUsersUseCase
from app.user.application.ports.output.user_port import UserPort


class ListUsersInteractor(ListUsersUseCase):
    def __init__(self, repository: UserPort) -> None:
        self._repository = repository

    def __call__(self, query: ListUsersQuery) -> ListUsersResult:
        offset = (query.page - 1) * query.size
        users, total = self._repository.list_users(
            q=query.q, offset=offset, limit=query.size
        )
        return ListUsersResult(
            items=[
                AdminUserSummary(
                    id=u.id,
                    email=str(u.email),
                    nickname=str(u.nickname),
                    created_at=u.created_at,
                )
                for u in users
            ],
            total=total,
            page=query.page,
            size=query.size,
        )
