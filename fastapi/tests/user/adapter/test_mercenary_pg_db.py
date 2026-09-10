"""용병 매칭 저장소가 **실제 PostgreSQL(pgvector)에서** 도는지 확인한다.

스텁(`test_mercenary_interactors.py`)은 코사인 유사도 순위를 흉내 내지 않는다
(주석 참고) — 그 부분과 `preferred_positions` 인코딩 왕복은 여기서만 본다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.user.adapter.outbound.pg.mercenary_pg_repository import MercenaryPgRepository
from app.user.domain.entities.mercenary_profile_entity import (
    AvailableSlot,
    MercenaryProfileEntity,
    PositionRef,
)

pytestmark = pytest.mark.db


def _new_session():
    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    return Session(engine)


@pytest.fixture
def two_users(db_session):
    ids = [uuid.uuid4(), uuid.uuid4()]
    for i, user_id in enumerate(ids):
        db_session.execute(
            text(
                'insert into "user" (id, email, nickname, created_at, token_version) '
                "values (:i, :e, :n, now(), 0)"
            ),
            {"i": user_id, "e": f"merc-{user_id}@example.test", "n": f"용병{i}"},
        )
    db_session.commit()
    yield ids
    for user_id in ids:
        db_session.execute(text('delete from "user" where id = :u'), {"u": user_id})
    db_session.commit()


def _unit_vector(dim: int, hot_index: int) -> list[float]:
    """`hot_index` 방향의 단위 벡터. 코사인 거리로 "가까움/멈"을 명확히 구분하려고
    직교 기저를 쓴다 — 실제 임베딩 분포를 흉내 내려는 게 아니다."""
    v = [0.0] * dim
    v[hot_index] = 1.0
    return v


def test_포지션_인코딩이_왕복한다(db_session, two_users):
    user_id = two_users[0]
    repo = MercenaryPgRepository(_new_session())
    profile = MercenaryProfileEntity(
        user_id=user_id,
        preferred_positions=[
            PositionRef(sport_code="football", code="GK"),
            PositionRef(sport_code="basketball", code="C"),
        ],
        available_slots=[AvailableSlot(day="SAT", start="18:00", end="21:00")],
        location="서울 강남",
        skill_summary="공중볼 처리에 강함",
        is_searchable=True,
        skill_embedding=_unit_vector(768, 0),
    )
    repo.save_profile(profile)

    reloaded = MercenaryPgRepository(_new_session()).get_profile(user_id)
    assert set((p.sport_code, p.code) for p in reloaded.preferred_positions) == {
        ("football", "GK"),
        ("basketball", "C"),
    }
    assert reloaded.location == "서울 강남"
    assert reloaded.is_searchable is True


def test_포지션_코드는_종목_간에_섞이지_않는다(db_session, two_users):
    """`C`는 야구 포수·농구 센터가 겹친다 — 다른 종목으로 검색하면 안 걸려야 한다."""
    user_id = two_users[0]
    repo = MercenaryPgRepository(_new_session())
    repo.save_profile(
        MercenaryProfileEntity(
            user_id=user_id,
            preferred_positions=[PositionRef(sport_code="baseball", code="C")],
            available_slots=[AvailableSlot(day="SAT", start="18:00", end="21:00")],
            skill_summary="포수",
            is_searchable=True,
            skill_embedding=_unit_vector(768, 0),
        )
    )

    basketball_results = MercenaryPgRepository(_new_session()).search_candidates(
        sport_code="basketball",
        position_code="C",
        query_embedding=_unit_vector(768, 0),
        limit=10,
    )
    assert user_id not in [c.user_id for c in basketball_results]

    baseball_results = MercenaryPgRepository(_new_session()).search_candidates(
        sport_code="baseball",
        position_code="C",
        query_embedding=_unit_vector(768, 0),
        limit=10,
    )
    assert user_id in [c.user_id for c in baseball_results]


def test_유사도_순으로_정렬된다(db_session, two_users):
    close_id, far_id = two_users
    repo = MercenaryPgRepository(_new_session())
    for user_id, hot_index in ((close_id, 0), (far_id, 1)):
        repo.save_profile(
            MercenaryProfileEntity(
                user_id=user_id,
                preferred_positions=[PositionRef(sport_code="football", code="GK")],
                available_slots=[AvailableSlot(day="SAT", start="18:00", end="21:00")],
                skill_summary="설명",
                is_searchable=True,
                skill_embedding=_unit_vector(768, hot_index),
            )
        )

    # 쿼리 벡터는 close_id와 같은 방향 — 코사인 유사도 1.0, far_id는 직교라 0.0.
    results = MercenaryPgRepository(_new_session()).search_candidates(
        sport_code="football",
        position_code="GK",
        query_embedding=_unit_vector(768, 0),
        limit=10,
    )
    assert [c.user_id for c in results] == [close_id, far_id]
    assert results[0].similarity == pytest.approx(1.0, abs=1e-6)
    assert results[1].similarity == pytest.approx(0.0, abs=1e-6)


def test_is_searchable_false면_검색에_안_나온다(db_session, two_users):
    user_id = two_users[0]
    repo = MercenaryPgRepository(_new_session())
    repo.save_profile(
        MercenaryProfileEntity(
            user_id=user_id,
            preferred_positions=[PositionRef(sport_code="football", code="GK")],
            available_slots=[AvailableSlot(day="SAT", start="18:00", end="21:00")],
            skill_summary="설명",
            is_searchable=False,
            skill_embedding=_unit_vector(768, 0),
        )
    )

    results = MercenaryPgRepository(_new_session()).search_candidates(
        sport_code="football",
        position_code="GK",
        query_embedding=_unit_vector(768, 0),
        limit=10,
    )
    assert user_id not in [c.user_id for c in results]
