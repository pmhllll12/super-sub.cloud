"""포지션 라우터. 계약 문서 3-3절.

읽기 전용 참조 데이터다. `squad` 등재·경기 `needs` 를 채우는 화면이 지금은
포지션 목록을 **하드코딩**하고 있어(마이그레이션이 바뀌면 조용히 낡는다),
그 자리를 이 엔드포인트로 갈아 끼운다.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserId
from app.user.adapter.inbound.api.schemas.position_schema import PositionResponse
from app.user.application.dtos.position_dto import ListPositionsQuery, PositionResult
from app.user.dependencies.position_providers import ListPositionsUseCaseDep

positions_router = APIRouter(tags=["positions"])


@positions_router.get("/positions", response_model=list[PositionResponse])
def list_positions(
    user_id: CurrentUserId,
    use_case: ListPositionsUseCaseDep,
    sport_code: str | None = Query(default=None, max_length=20),
) -> list[PositionResult]:
    """종목별 포지션 목록. 로그인하면 누구나.

    `?sport_code=football` 로 한 종목만, 없으면 전 종목(`sport_code` 순).
    🔴 **없는 종목으로 거르면 `422 UNKNOWN_SPORT`** — 빈 배열이면 오타와
    "그 종목 포지션이 아직 없다"가 같아 보인다(`GET /matches` 와 같은 판단).
    """
    return use_case(ListPositionsQuery(sport_code=sport_code))
