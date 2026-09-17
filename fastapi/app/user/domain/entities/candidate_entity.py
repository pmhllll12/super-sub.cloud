"""용병 후보 검색 결과 1건."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.user.domain.entities.mercenary_profile_entity import PositionRef


@dataclass(frozen=True)
class CandidateEntity:
    user_id: UUID
    nickname: str
    location: str | None
    skill_summary: str | None
    preferred_positions: list[PositionRef]
    # 코사인 유사도(1에 가까울수록 비슷함). pgvector `<=>`는 거리(1 - 유사도)를
    # 돌려주므로 저장소 구현이 `1 - distance`로 바꿔서 채운다.
    similarity: float
