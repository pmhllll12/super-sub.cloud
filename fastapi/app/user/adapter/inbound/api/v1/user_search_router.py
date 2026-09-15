"""사용자 검색 라우터. 계약 문서 3-12절. 미결 `jin` 35번.

지인 신청 전에 상대를 찾는 자리다. `is_nickname_searchable=false`로 끈 사람은
안 나온다.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.user_contact_schema import (
    UserSearchItemResponse,
)
from app.user.application.dtos.user_contact_dto import SearchUsersQuery
from app.user.dependencies.search_users_provider import SearchUsersUseCaseDep

user_search_router = APIRouter(tags=["users"])


@user_search_router.get("/users/search", response_model=list[UserSearchItemResponse])
def search_users(
    user_id: CurrentUserId,
    use_case: SearchUsersUseCaseDep,
    q: str = Query(min_length=1, max_length=20),
):
    """닉네임 부분일치(대소문자 무관), 최대 20명. 본인은 결과에서 빠진다."""
    return use_case(SearchUsersQuery(actor_id=user_id, q=q))
