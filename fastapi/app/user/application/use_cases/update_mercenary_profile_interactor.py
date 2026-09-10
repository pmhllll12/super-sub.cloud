"""내 용병 프로필 수정 인터랙터.

병합 규칙(PATCH 의미):
- 커맨드 필드가 `None`이면 **건드리지 않는다.**
- 문자열 필드(`location`·`skill_summary`)는 빈 문자열("")을 보내면 **지운다**
  (`None`으로 저장) — "안 보냄"과 "지움"을 구분하는 유일한 방법이다.
- 리스트 필드(`preferred_positions`·`available_slots`)는 빈 리스트를 보내면
  그대로 빈 리스트로 저장한다(리스트는 `None`과 `[]`를 코드로 구분할 수 있어
  문자열과 달리 이런 우회가 필요 없다).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from app.core.errors import ApiError
from app.user.application.dtos.mercenary_dto import (
    AvailableSlotDto,
    MercenaryProfileResult,
    PositionRefDto,
    UpdateMercenaryProfileCommand,
)
from app.user.application.ports.input.update_mercenary_profile_use_case import (
    UpdateMercenaryProfileUseCase,
)
from app.user.application.ports.output.embedding_port import EmbeddingPort
from app.user.application.ports.output.mercenary_port import MercenaryPort
from app.user.domain.entities.mercenary_profile_entity import AvailableSlot, PositionRef


def _to_domain_positions(dtos: list[PositionRefDto]) -> list[PositionRef]:
    return [PositionRef(sport_code=d.sport_code, code=d.code) for d in dtos]


def _to_domain_slots(dtos: list[AvailableSlotDto]) -> list[AvailableSlot]:
    return [AvailableSlot(day=d.day, start=d.start, end=d.end) for d in dtos]


class UpdateMercenaryProfileInteractor(UpdateMercenaryProfileUseCase):
    def __init__(
        self, repository: MercenaryPort, embedder_factory: Callable[[], EmbeddingPort]
    ) -> None:
        """`embedder_factory`는 **팩토리**다(이미 만들어진 어댑터가 아니라).

        `skill_summary`를 안 건드리는 요청(포지션·가능 시간만 바꾸는 등)은
        임베딩 어댑터가 아예 필요 없다 — 즉시 만들면 `GEMINI_API_KEY`가 아직
        없는 환경에서 그런 요청까지 503으로 막힌다. 실제로 쓸 때만 만든다.
        """
        self._repository = repository
        self._embedder_factory = embedder_factory

    def __call__(
        self, command: UpdateMercenaryProfileCommand
    ) -> MercenaryProfileResult:
        current = self._repository.get_profile(command.user_id)

        location = current.location
        if command.location is not None:
            location = command.location or None

        skill_summary_changed = False
        skill_summary = current.skill_summary
        if command.skill_summary is not None:
            new_summary = command.skill_summary or None
            skill_summary_changed = new_summary != current.skill_summary
            skill_summary = new_summary

        preferred_positions = (
            _to_domain_positions(command.preferred_positions)
            if command.preferred_positions is not None
            else current.preferred_positions
        )
        available_slots = (
            _to_domain_slots(command.available_slots)
            if command.available_slots is not None
            else current.available_slots
        )
        is_searchable = (
            command.is_searchable
            if command.is_searchable is not None
            else current.is_searchable
        )

        if is_searchable and not (
            preferred_positions and available_slots and skill_summary
        ):
            # 원래 마이그레이션 의도(`user_orm.py` 주석) 그대로 — 포지션·가능
            # 시간·소개를 다 채운 사람만 검색 대상에 노출한다. 빈 프로필이
            # 노출되면 검색 결과가 전부 의미 없는 카드가 된다.
            raise ApiError(
                422,
                "MERCENARY_PROFILE_INCOMPLETE",
                "검색에 노출되려면 포지션·가능 시간·소개를 모두 채워야 합니다.",
            )

        # 소개(skill_summary)가 실제로 바뀐 요청에서만 다시 계산한다 — 매 PATCH
        # 마다 부르면 포지션만 바꾸는 흔한 요청에도 임베딩 API를 태운다.
        skill_embedding = current.skill_embedding
        if skill_summary_changed:
            skill_embedding = (
                self._embedder_factory().embed(skill_summary, purpose="document")
                if skill_summary
                else None
            )

        updated = replace(
            current,
            location=location,
            skill_summary=skill_summary,
            preferred_positions=preferred_positions,
            available_slots=available_slots,
            is_searchable=is_searchable,
            skill_embedding=skill_embedding,
        )
        self._repository.save_profile(updated)

        return MercenaryProfileResult(
            user_id=updated.user_id,
            preferred_positions=[
                PositionRefDto(sport_code=p.sport_code, code=p.code)
                for p in updated.preferred_positions
            ],
            available_slots=[
                AvailableSlotDto(day=s.day, start=s.start, end=s.end)
                for s in updated.available_slots
            ],
            location=updated.location,
            skill_summary=updated.skill_summary,
            is_searchable=updated.is_searchable,
        )
