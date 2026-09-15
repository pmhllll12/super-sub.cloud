"""지역 라우터. `paik` 19번.

읽기 전용 참조 데이터다. `www/src/lib/regions.ts`가 지금 60여 곳을 하드코딩
하고 있고, 저장되는 값이 자유 입력이면 "강남구"·"서울 강남구"가 다른 값으로
저장돼 지역 계층 비교(`paik` 20번)가 깨진다 — `GET /positions`와 같은 결로
연다.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.region_schema import RegionResponse
from app.user.application.dtos.region_dto import ListRegionsQuery, RegionResult
from app.user.dependencies.region_providers import ListRegionsUseCaseDep

regions_router = APIRouter(tags=["regions"])


@regions_router.get("/regions", response_model=list[RegionResponse])
def list_regions(
    _user_id: CurrentUserId, use_case: ListRegionsUseCaseDep
) -> list[RegionResult]:
    """전체 지역 목록. 로그인하면 누구나."""
    return use_case(ListRegionsQuery())
