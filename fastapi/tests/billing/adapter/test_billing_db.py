"""과금이 **실제 PostgreSQL에서** 도는지 확인한다.

계약 테스트(`test_billing_router.py`)는 스텁을 끼우므로 FK·정렬을 보지 못한다.
여기서 보는 것은 셋이다.

1. `user`를 원시 쿼리로 읽는 자리(`user_exists`)가 맞다 — 🔴 저쪽 컬럼 이름이
   바뀌면 파이썬이 안 잡아 준다. 이 검사가 유일한 방어선이다 — **지우지 말 것**
2. 크레딧 잔량이 실제로 `SUM(delta)`로 나온다 — 컬럼이 없다
3. `coach_referral`에 유일 제약이 없다 — 같은 코치에 여러 번 연결해도 전부 남는다
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.billing.adapter.outbound.pg.billing_pg_repository import BillingPgRepository
from app.billing.domain.entities.billing_entity import (
    CoachEntity,
    CoachReferralEntity,
    CreditEntryEntity,
)

pytestmark = pytest.mark.db


def _new_session():
    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    return Session(engine)


@pytest.fixture
def user(db_session):
    user_id = uuid.uuid4()
    db_session.execute(
        text(
            'insert into "user" (id, email, nickname, created_at, token_version) '
            "values (:i, :e, :n, now(), 0)"
        ),
        {"i": user_id, "e": f"bill-{user_id}@example.test", "n": "과금검사"},
    )
    db_session.commit()
    yield user_id
    db_session.execute(
        text("delete from coach_referral where user_id = :u"), {"u": user_id}
    )
    db_session.execute(
        text("delete from analysis_credit where user_id = :u"), {"u": user_id}
    )
    db_session.execute(text('delete from "user" where id = :u'), {"u": user_id})
    db_session.commit()


@pytest.fixture
def coach(db_session):
    repo = BillingPgRepository(_new_session())
    c = CoachEntity(id=uuid.uuid4(), name="검사코치", contact="test@example.test")
    db_session.execute(
        text("insert into coach (id, name, contact) values (:i, :n, :c)"),
        {"i": c.id, "n": c.name, "c": c.contact},
    )
    db_session.commit()
    yield c
    db_session.execute(
        text("delete from coach_referral where coach_id = :i"), {"i": c.id}
    )
    db_session.execute(text("delete from coach where id = :i"), {"i": c.id})
    db_session.commit()


def test_남의_테이블을_읽는_자리가_맞다(db_session, user):
    repo = BillingPgRepository(_new_session())
    assert repo.user_exists(user)
    assert not repo.user_exists(uuid.uuid4())


def test_잔량은_SUM_delta다(db_session, user):
    repo = BillingPgRepository(_new_session())
    now = datetime.now(timezone.utc)
    repo.add_credit_entry(
        CreditEntryEntity(uuid.uuid4(), user, 100, "signup_bonus", now)
    )
    repo.add_credit_entry(CreditEntryEntity(uuid.uuid4(), user, -30, "analysis", now))

    history = BillingPgRepository(_new_session()).credit_history(user)
    assert [h.delta for h in history] == [100, -30]
    assert sum(h.delta for h in history) == 70


def test_코치_연결은_유일_제약이_없다(db_session, user, coach):
    repo = BillingPgRepository(_new_session())
    now = datetime.now(timezone.utc)
    for _ in range(2):
        repo.save_referral(
            CoachReferralEntity(uuid.uuid4(), user, coach.id, Decimal("10000.00"), now)
        )

    n = db_session.execute(
        text("select count(*) from coach_referral where user_id = :u"), {"u": user}
    ).scalar_one()
    assert n == 2


def test_코치_목록은_이름순으로_페이지네이션된다(db_session, coach):
    repo = BillingPgRepository(_new_session())
    coaches, total = repo.list_coaches(offset=0, limit=100)
    assert total >= 1
    assert any(c.id == coach.id for c in coaches)


def test_없는_코치는_None이다(db_session):
    repo = BillingPgRepository(_new_session())
    assert repo.get_coach(uuid.uuid4()) is None
