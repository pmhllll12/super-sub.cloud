"""내 용병 프로필 조회 인터랙터."""

from __future__ import annotations

from app.user.application.dtos.mercenary_dto import (
    AvailableSlotDto,
    GetMercenaryProfileQuery,
    MercenaryProfileResult,
    PositionRefDto,
)
from app.user.application.ports.input.get_mercenary_profile_use_case import (
    GetMercenaryProfileUseCase,
)
from app.user.application.ports.output.mercenary_port import MercenaryPort


class GetMercenaryProfileInteractor(GetMercenaryProfileUseCase):
    def __init__(self, repository: MercenaryPort) -> None:
        self._repository = repository

    def __call__(self, query: GetMercenaryProfileQuery) -> MercenaryProfileResult:
        profile = self._repository.get_profile(query.user_id)
        return MercenaryProfileResult(
            user_id=profile.user_id,
            preferred_positions=[
                PositionRefDto(sport_code=p.sport_code, code=p.code)
                for p in profile.preferred_positions
            ],
            available_slots=[
                AvailableSlotDto(day=s.day, start=s.start, end=s.end)
                for s in profile.available_slots
            ],
            location=profile.location,
            skill_summary=profile.skill_summary,
            is_searchable=profile.is_searchable,
        )
