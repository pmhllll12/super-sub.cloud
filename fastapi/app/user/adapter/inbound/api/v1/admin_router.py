"""회원 관리(admin) 라우터.

**여기는 도메인을 모른다.** 인바운드 스키마는 관례대로 `app/user/adapter/inbound/`
에 두지만, 관리자 게이트(`require_admin`)는 컨텍스트를 모르는 공용
모듈(`app/core/deps.py`)에 있다 — user·card 양쪽에서 admin 라우터가 생겨도
게이트 로직이 갈라지지 않게 하기 위해서다.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAdminUserId
from app.user.adapter.inbound.api.schemas.admin_schema import (
    AdminUserDetailResponse,
    AdminUserListResponse,
)
from app.user.application.dtos.admin_dto import (
    AdminUserDetailQuery,
    AdminUserDetailResult,
    ForceDeleteUserCommand,
    ListUsersQuery,
    ListUsersResult,
)
from app.user.dependencies.admin_user_detail_provider import AdminUserDetailUseCaseDep
from app.user.dependencies.force_delete_user_provider import (
    ForceDeleteUserUseCaseDep,
)
from app.user.dependencies.list_users_provider import ListUsersUseCaseDep

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/users", response_model=AdminUserListResponse)
def list_users(
    _admin_id: CurrentAdminUserId,
    use_case: ListUsersUseCaseDep,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> ListUsersResult:
    return use_case(ListUsersQuery(q=q, page=page, size=size))


@admin_router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def read_user(
    user_id: UUID,
    _admin_id: CurrentAdminUserId,
    use_case: AdminUserDetailUseCaseDep,
) -> AdminUserDetailResult:
    return use_case(AdminUserDetailQuery(user_id=user_id))


@admin_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    _admin_id: CurrentAdminUserId,
    use_case: ForceDeleteUserUseCaseDep,
) -> None:
    """관리자가 회원을 강제 탈퇴시킨다. `DELETE /me` 와 달리 비밀번호를 요구하지 않는다."""
    use_case(ForceDeleteUserCommand(user_id=user_id))
