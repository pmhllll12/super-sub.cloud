"""`MercenaryPort`의 고정 데이터 저장소. DB 없이 계약 테스트를 돌리는 자리다."""

from __future__ import annotations

from uuid import UUID

from app.user.application.ports.output.mercenary_port import MercenaryPort
from app.user.domain.entities.candidate_entity import CandidateEntity
from app.user.domain.entities.mercenary_profile_entity import MercenaryProfileEntity


class MercenaryStubRepository(MercenaryPort):
    def __init__(self) -> None:
        self._profiles: dict[UUID, MercenaryProfileEntity] = {}

    def get_profile(self, user_id: UUID) -> MercenaryProfileEntity:
        return self._profiles.get(user_id) or MercenaryProfileEntity(user_id=user_id)

    def save_profile(self, profile: MercenaryProfileEntity) -> None:
        self._profiles[profile.user_id] = profile

    def search_candidates(
        self,
        *,
        sport_code: str,
        position_code: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[CandidateEntity]:
        # 실제 코사인 유사도를 흉내 내지 않는다 — 스텁은 "찾는 조건에 맞는
        # 사람만 나온다"만 검증하면 되고, 순위 품질은 DB 통합 테스트(pgvector)의
        # 몫이다. 저장된 순서대로, 매칭되는 만큼만 유사도 1.0으로 돌려준다.
        matches = [
            p
            for p in self._profiles.values()
            if p.is_searchable
            and any(
                ref.sport_code == sport_code and ref.code == position_code
                for ref in p.preferred_positions
            )
        ]
        return [
            CandidateEntity(
                user_id=p.user_id,
                nickname=f"user-{p.user_id}",
                location=p.location,
                skill_summary=p.skill_summary,
                preferred_positions=p.preferred_positions,
                similarity=1.0,
            )
            for p in matches[:limit]
        ]
