"""평가·신뢰가 **실제 PostgreSQL 에서** 도는지 확인한다.

계약 테스트(`test_review_router.py`)는 스텁을 끼우므로 조인·유일 제약을 보지
못한다. 여기서 보는 것은 셋이다.

1. 유일 제약이 **DB 에 실재한다**(부록 D.7) — 파이썬이 아니라 DB 가 막는다
2. **남의 테이블을 원시 쿼리로 읽는 자리**가 맞다 — `match`·`match_application`·
   `team_member`·`user`. 🔴 저쪽 컬럼 이름이 바뀌면 파이썬이 안 잡아 준다.
   이 검사가 유일한 방어선이다 — **지우지 말 것**
3. 선택지가 `sort_order` 순으로 나온다 — `label` 을 고쳐도 순서가 안 바뀐다
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.review.adapter.outbound.pg.review_pg_repository import ReviewPgRepository
from app.review.domain.entities.review_entity import (
    NoShowEntity,
    ReportEntity,
    ReviewEntity,
)

pytestmark = pytest.mark.db


def _new_session():
    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    return Session(engine)


@pytest.fixture
def played(db_session):
    """어제 끝난 경기 하나 — 주장과 용병이 **확정**돼 있다."""
    owner, mercenary = uuid.uuid4(), uuid.uuid4()
    team_id, match_id = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)

    for uid, nick in ((owner, "주장"), (mercenary, "용병")):
        db_session.execute(
            text('insert into "user" (id, email, nickname, created_at, token_version) '
                 "values (:i, :e, :n, now(), 0)"),
            {"i": uid, "e": f"rv-{uid}@example.test", "n": nick},
        )
    # ⚠️ `team` 은 `id·name·region·sport_code` 뿐이다 — `owner_id`·`created_at`
    #    이 없다(실측). 주장은 `team_member.role` 이 말한다.
    db_session.execute(
        text("insert into team (id, name, sport_code, region) "
             "values (:i, :n, 'football', '서울')"),
        {"i": team_id, "n": f"평가검사팀-{team_id.hex[:6]}"},
    )
    db_session.execute(
        text("insert into team_member (id, team_id, user_id, role, joined_at) "
             "values (:i, :t, :u, 'owner', now())"),
        {"i": uuid.uuid4(), "t": team_id, "u": owner},
    )
    db_session.execute(
        text("insert into match (id, team_id, played_at, place) "
             "values (:i, :t, :p, '검사구장')"),
        {"i": match_id, "t": team_id, "p": now - timedelta(days=1)},
    )
    # 🔴 두 수락 시각이 **다 차야** 확정이다 (부록 D.5).
    for uid in (owner, mercenary):
        db_session.execute(
            text("insert into match_application "
                 "(id, match_id, user_id, team_accepted_at, user_accepted_at) "
                 "values (:i, :m, :u, now(), now())"),
            {"i": uuid.uuid4(), "m": match_id, "u": uid},
        )
    db_session.commit()

    yield {"match_id": match_id, "team_id": team_id, "owner": owner,
           "mercenary": mercenary}

    for stmt in (
        "delete from review_selection where review_id in "
        "(select id from review where match_id = :m)",
        "delete from review where match_id = :m",
        "delete from no_show where match_id = :m",
        "delete from match_application where match_id = :m",
        "delete from match where id = :m",
    ):
        db_session.execute(text(stmt), {"m": match_id})
    db_session.execute(
        text("delete from report where reporter_id = :a or target_user_id = :a"),
        {"a": owner},
    )
    db_session.execute(
        text("delete from report where reporter_id = :a or target_user_id = :a"),
        {"a": mercenary},
    )
    db_session.execute(text("delete from team_member where team_id = :t"), {"t": team_id})
    db_session.execute(text("delete from team where id = :t"), {"t": team_id})
    db_session.execute(
        text('delete from "user" where id in (:a, :b)'),
        {"a": owner, "b": mercenary},
    )
    db_session.commit()


def _review(played, **kw):
    return ReviewEntity(
        id=kw.get("id", uuid.uuid4()),
        match_id=played["match_id"],
        reviewer_id=kw.get("reviewer", played["owner"]),
        reviewee_id=kw.get("reviewee", played["mercenary"]),
        submitted_at=datetime.now(timezone.utc),
        selected_codes=kw.get("codes", ["manner_time", "skill_teamplay"]),
    )


def test_남의_테이블을_읽는_자리가_맞다(db_session, played):
    """🔴 `match`·`match_application`·`team_member` 를 원시 쿼리로 읽는다."""
    repo = ReviewPgRepository(_new_session())

    assert repo.match_played_at(played["match_id"]) is not None
    assert repo.match_played_at(uuid.uuid4()) is None
    assert repo.team_role_of(played["match_id"], played["owner"]) == "owner"
    assert repo.team_role_of(played["match_id"], played["mercenary"]) is None
    assert repo.is_confirmed_participant(played["match_id"], played["mercenary"])
    assert not repo.is_confirmed_participant(played["match_id"], uuid.uuid4())
    assert repo.user_exists(played["owner"])


def test_확정되지_않은_지원은_참가자가_아니다(db_session, played):
    """한쪽 시각만 찬 행은 **아직 확정이 아니다**(부록 D.5)."""
    pending = uuid.uuid4()
    db_session.execute(
        text('insert into "user" (id, email, nickname, created_at, token_version) '
             "values (:i, :e, '대기', now(), 0)"),
        {"i": pending, "e": f"pend-{pending}@example.test"},
    )
    db_session.execute(
        text("insert into match_application "
             "(id, match_id, user_id, team_accepted_at, user_accepted_at) "
             "values (:i, :m, :u, null, now())"),
        {"i": uuid.uuid4(), "m": played["match_id"], "u": pending},
    )
    db_session.commit()

    repo = ReviewPgRepository(_new_session())
    assert not repo.is_confirmed_participant(played["match_id"], pending)

    db_session.execute(
        text("delete from match_application where user_id = :u"), {"u": pending}
    )
    db_session.execute(text('delete from "user" where id = :u'), {"u": pending})
    db_session.commit()


def test_평가와_선택이_함께_저장된다(db_session, played):
    review = _review(played)
    assert ReviewPgRepository(_new_session()).save_review(review) is True

    got = db_session.execute(
        text("select count(*) from review_selection where review_id = :r"),
        {"r": review.id},
    ).scalar_one()
    assert got == 2, "선택 결과가 행으로 남아야 한다"


def test_경기당_1회_평가가_DB_제약으로_막힌다(db_session, played):
    """🔴 파이썬이 아니라 **DB** 가 막는지 본다 (부록 D.7)."""
    assert ReviewPgRepository(_new_session()).save_review(_review(played)) is True
    assert ReviewPgRepository(_new_session()).save_review(_review(played)) is False

    n = db_session.execute(
        text("select count(*) from review where match_id = :m"),
        {"m": played["match_id"]},
    ).scalar_one()
    assert n == 1


def test_반대_방향_평가는_따로_들어간다(db_session, played):
    """(match, reviewer, reviewee) 유일이라 **서로 평가**는 둘 다 된다."""
    repo = ReviewPgRepository(_new_session())
    assert repo.save_review(_review(played)) is True
    assert repo.save_review(
        _review(played, reviewer=played["mercenary"], reviewee=played["owner"])
    ) is True


def test_불참은_경기당_1인_1건이다(db_session, played):
    def no_show():
        return NoShowEntity(
            id=uuid.uuid4(),
            match_id=played["match_id"],
            user_id=played["mercenary"],
            recorded_at=datetime.now(timezone.utc),
        )

    assert ReviewPgRepository(_new_session()).save_no_show(no_show()) is True
    assert ReviewPgRepository(_new_session()).save_no_show(no_show()) is False


def test_신고는_중복을_막지_않는다(db_session, played):
    """같은 사람을 여러 번 신고할 수 있다 — 유일 제약이 없다."""
    repo = ReviewPgRepository(_new_session())
    for _ in range(2):
        repo.save_report(
            ReportEntity(
                id=uuid.uuid4(),
                reporter_id=played["owner"],
                target_user_id=played["mercenary"],
                reason="검사용",
                created_at=datetime.now(timezone.utc),
            )
        )
    n = db_session.execute(
        text("select count(*) from report where target_user_id = :t"),
        {"t": played["mercenary"]},
    ).scalar_one()
    assert n == 2


def test_선택지는_sort_order_순으로_온다(db_session):
    """🔴 `label` 을 고쳐도 순서가 안 바뀌어야 한다 — 그게 컬럼을 늘린 이유다."""
    repo = ReviewPgRepository(_new_session())
    before = [o.code for o in repo.list_options()]
    assert before[0] == "manner_time"
    assert before[-1] == "caution_would_not_repeat"

    db_session.execute(
        text("update review_option set label = :l where code = 'manner_time'"),
        {"l": "시간을 잘 지켰습니다"},
    )
    db_session.commit()
    try:
        assert [o.code for o in ReviewPgRepository(_new_session()).list_options()] == before
    finally:
        db_session.execute(
            text("update review_option set label = :l where code = 'manner_time'"),
            {"l": "시간을 잘 지켰다"},
        )
        db_session.commit()
