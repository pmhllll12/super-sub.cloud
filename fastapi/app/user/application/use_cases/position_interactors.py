"""포지션 조회 인터랙터."""

from __future__ import annotations

from app.user.application.dtos.position_dto import (
    ListPositionsQuery,
    PositionResult,
)
from app.user.application.ports.input.position_use_cases import (
    ListPositionsUseCase,
)
from app.user.application.ports.output.position_port import PositionPort
from app.core.errors import ApiError


class ListPositionsInteractor(ListPositionsUseCase):
    def __init__(self, repository: PositionPort) -> None:
        self._repository = repository

    def __call__(self, query: ListPositionsQuery) -> list[PositionResult]:
        # 🔴 오타 종목은 빈 목록이 아니라 422 다 — `GET /matches` 와 같은 판단.
        #    빈 목록으로 답하면 "오타"와 "그 종목 포지션이 아직 없다"가 같아 보인다.
        if query.sport_code is not None and not self._repository.sport_exists(
            query.sport_code
        ):
            raise ApiError(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다.")

        return [
            PositionResult(
                sport_code=p.sport_code, code=p.code, label=p.label
            )
            for p in self._repository.list_positions(query.sport_code)
        ]
