"""`MercenaryPort`의 PostgreSQL(pgvector) 구현.

포지션 인코딩: `preferred_positions`는 `ARRAY(String)` 컬럼이라 `PositionRef`
쌍을 `"<sport_code>:<code>"` 문자열로 직렬화해 담는다(엔티티 쪽 주석 참고) —
이 파일 밖으로 새어 나가지 않는 순전히 저장소 내부 표현이다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.mercenary_port import MercenaryPort
from app.user.domain.entities.candidate_entity import CandidateEntity
from app.user.domain.entities.mercenary_profile_entity import (
    AvailableSlot,
    MercenaryProfileEntity,
    PositionRef,
)

_SEP = ":"


def _encode_position(ref: PositionRef) -> str:
    return f"{ref.sport_code}{_SEP}{ref.code}"


def _decode_position(raw: str) -> PositionRef:
    sport_code, _, code = raw.partition(_SEP)
    return PositionRef(sport_code=sport_code, code=code)


def _to_profile(row: UserOrm) -> MercenaryProfileEntity:
    return MercenaryProfileEntity(
        user_id=row.id,
        preferred_positions=[
            _decode_position(p) for p in (row.preferred_positions or [])
        ],
        available_slots=[
            AvailableSlot(day=s["day"], start=s["start"], end=s["end"])
            for s in (row.available_slots or [])
        ],
        location=row.location,
        skill_summary=row.skill_summary,
        is_searchable=row.is_searchable,
        skill_embedding=(
            list(row.skill_embedding) if row.skill_embedding is not None else None
        ),
    )


class MercenaryPgRepository(MercenaryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_profile(self, user_id: UUID) -> MercenaryProfileEntity:
        row = self._session.get(UserOrm, user_id)
        if row is None:
            # 유스케이스가 이미 `UserPort.get`으로 존재를 확인한 뒤 부르는
            # 경로다 — 여기서 404 낼 일이 아니라 빈 프로필로 넘긴다.
            return MercenaryProfileEntity(user_id=user_id)
        return _to_profile(row)

    def save_profile(self, profile: MercenaryProfileEntity) -> None:
        row = self._session.get(UserOrm, profile.user_id)
        if row is None:
            return
        row.preferred_positions = [
            _encode_position(p) for p in profile.preferred_positions
        ]
        row.available_slots = [
            {"day": s.day, "start": s.start, "end": s.end}
            for s in profile.available_slots
        ]
        row.location = profile.location
        row.skill_summary = profile.skill_summary
        row.is_searchable = profile.is_searchable
        row.skill_embedding = profile.skill_embedding
        self._session.commit()

    def search_candidates(
        self,
        *,
        sport_code: str,
        position_code: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[CandidateEntity]:
        encoded = _encode_position(PositionRef(sport_code=sport_code, code=position_code))
        distance = UserOrm.skill_embedding.cosine_distance(query_embedding)
        stmt = (
            select(UserOrm, distance.label("distance"))
            .where(UserOrm.is_searchable.is_(True))
            .where(UserOrm.skill_embedding.is_not(None))
            .where(UserOrm.preferred_positions.contains([encoded]))
            .order_by(distance)
            .limit(limit)
        )
        rows = self._session.execute(stmt).all()
        return [
            CandidateEntity(
                user_id=row.id,
                nickname=row.nickname,
                location=row.location,
                skill_summary=row.skill_summary,
                preferred_positions=[
                    _decode_position(p) for p in (row.preferred_positions or [])
                ],
                similarity=1.0 - distance_value,
            )
            for row, distance_value in rows
        ]
