"""선수·관절(skeleton) 라우터. 계약 문서. `paik` 29번.

「선수와 비교하기」가 비교할 자세를 겹쳐 그리는 자리에 필요한 서버 몫이다.
지금 화면은 브라우저가 직접 관절을 뽑는다(MoveNet) — 이 API가 붙으면
`www/src/lib/motion/source.ts`(받는 자리가 한 곳)만 바꾸면 된다.

🔴 **재생 주소는 안 준다.** 선수 원본 영상이 S3에 없다(EC2 역할이 `videos/`
접두사에 쓰기 권한이 없어 못 올렸다) — 화면은 계속 정적 파일
(`www/public/compare/`)로 재생한다.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.analysis.adapter.inbound.api.schemas.reference_player_schema import (
    ReferencePlayerResponse,
    SkeletonResponse,
)
from app.analysis.application.dtos.reference_player_dto import (
    GetReferencePlayerSkeletonQuery,
    GetVideoSkeletonQuery,
    ListReferencePlayersQuery,
    ReferencePlayerResult,
    SkeletonResult,
)
from app.analysis.dependencies.reference_player_providers import (
    GetReferencePlayerSkeletonUseCaseDep,
    GetVideoSkeletonUseCaseDep,
    ListReferencePlayersUseCaseDep,
)
from app.core.deps import CurrentUserId

reference_player_router = APIRouter(tags=["reference-players"])


@reference_player_router.get(
    "/reference-players", response_model=list[ReferencePlayerResponse]
)
def list_reference_players(
    _user_id: CurrentUserId, use_case: ListReferencePlayersUseCaseDep
) -> list[ReferencePlayerResult]:
    """비교 화면이 고를 수 있는 선수 목록. 로그인하면 누구나."""
    return use_case(ListReferencePlayersQuery())


@reference_player_router.get(
    "/reference-players/{player_id}/skeleton", response_model=SkeletonResponse
)
def get_reference_player_skeleton(
    player_id: str,
    _user_id: CurrentUserId,
    use_case: GetReferencePlayerSkeletonUseCaseDep,
) -> SkeletonResult:
    """그 선수의 관절 시계열. 없는 선수면 `404 PLAYER_NOT_FOUND`."""
    return use_case(GetReferencePlayerSkeletonQuery(player_id=player_id))


@reference_player_router.get(
    "/videos/{video_id}/skeleton", response_model=SkeletonResponse
)
def get_video_skeleton(
    video_id: UUID,
    user_id: CurrentUserId,
    use_case: GetVideoSkeletonUseCaseDep,
) -> SkeletonResult:
    """**내 영상만**의 관절 시계열. `GET /videos/{id}/report`와 같은 에러 셋
    — 없거나 남의 것이면 `404 VIDEO_NOT_FOUND`, 분석 실패면
    `404 ANALYSIS_FAILED`, 아직 안 끝났으면 `404 REPORT_NOT_READY`.
    """
    return use_case(GetVideoSkeletonQuery(video_id=video_id, user_id=user_id))
