"""관리자 영상 관리 라우터. 계약 문서 3-2절(미결 `jin` 24번).

**여기는 도메인을 모른다.** 관리자 게이트(`require_admin`)는 컨텍스트를 모르는
공용 모듈(`app/core/deps.py`)에 있다 — `user` 의 admin 라우터와 게이트 로직이
갈라지지 않게 하기 위해서다(`user/adapter/.../admin_router.py` 와 같은 판단).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.analysis.adapter.inbound.api.schemas.video_schema import (
    AdminVideoListResponse,
)
from app.analysis.application.dtos.video_dto import (
    AdminDeleteVideoCommand,
    AdminVideoListResult,
    AdminVideosQuery,
)
from app.analysis.dependencies.video_providers import (
    AdminDeleteVideoUseCaseDep,
    ListAdminVideosUseCaseDep,
)
from app.core.deps import CurrentAdminUserId

admin_video_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_video_router.get("/videos", response_model=AdminVideoListResponse)
def list_admin_videos(
    _admin_id: CurrentAdminUserId,
    use_case: ListAdminVideosUseCaseDep,
    user: str = Query(min_length=1, description="user.id(UUID) 또는 이메일"),
) -> AdminVideoListResult:
    """한 사람의 영상을 **전부** 본다 — 아직 저장 안 한 임시분까지.

    사람이 문제 영상을 찾아 지우고 "에이전트가 제대로 돌았는지" 확인하는
    자리다. 없는 사람이면 `404 USER_NOT_FOUND`.
    """
    return use_case(AdminVideosQuery(identifier=user))


@admin_video_router.delete(
    "/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_admin_video(
    video_id: UUID,
    admin_id: CurrentAdminUserId,
    use_case: AdminDeleteVideoUseCaseDep,
) -> None:
    """관리자가 **아무** 영상이나 지운다 — DB 연쇄 + S3(best-effort).

    `DELETE /videos/{id}` 와 달리 소유를 확인하지 않는다. 누가 눌렀는지는
    서버 로그에 남긴다(`event=admin_delete_video`). 없는 클립이면 `404`.
    """
    use_case(AdminDeleteVideoCommand(video_id=video_id, admin_id=admin_id))
