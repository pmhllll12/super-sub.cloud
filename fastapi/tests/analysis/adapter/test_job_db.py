"""큐를 집는 자리가 **실제 PostgreSQL 에서** 안전한지 확인한다.

계약 테스트(`test_job_router.py`)는 스텁을 끼우므로 **동시성을 볼 수 없다** —
파이썬 딕셔너리에는 행 잠금이 없어서, 두 워커가 같은 작업을 집는 버그가
거기서는 통과한다. 여기가 그 유일한 방어선이다.

보는 것 셋.

1. `FOR UPDATE` — 잠긴 행을 다른 워커가 **가져가지 않는다**
2. `SKIP LOCKED` — 그러면서 **멈춰 서지도 않는다**(다음 것을 집는다)
3. `finish` 가 `running` 일 때만 바꾼다 (조건이 SQL 에 있다)

🔴 **`lock_timeout` 을 걸고 검사한다.** 안 걸면 `SKIP LOCKED` 를 빼먹었을 때
검사가 **실패가 아니라 영원히 멈춘다** — 그런 검사는 아무도 안 돌리게 된다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.pg.job_pg_repository import JobPgRepository
from app.analysis.domain.rules.job_rules import QUEUED, RUNNING

pytestmark = pytest.mark.db


def _new_session():
    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    return Session(engine)


#: 🔴 **개발 DB 의 큐는 비어 있지 않다.** `test_video_db.py` 가 업로드를 검사하며
#: 만든 작업이 백 건 넘게 `queued` 로 남아 있다(2026-09-04 확인: 151 건). 그것들이
#: 내 것보다 오래됐으면 `claim_next` 는 **남의 것을 집는다** — 실제로 그렇게 깨졌고,
#: 그 과정에서 leftover 다섯 건을 `running` 으로 바꿔 놓았다(되돌렸다).
#:
#: 그래서 **내 것을 아주 오래된 시각으로 넣는다.** 남의 행을 건드리지 않고 순서를
#: 확정하는 방법이다. 큐를 비우거나 남의 행 상태를 바꾸는 쪽은 되돌리기가 필요해서
#: 안 쓴다.
_ANCIENT = datetime(2000, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def queued(db_session):
    """영상 둘과 그 작업 둘을 큐에 넣는다. 뒤엣것이 더 오래됐다."""
    user_id = uuid.uuid4()
    db_session.execute(
        text('insert into "user" (id, email, nickname, created_at, token_version) '
             "values (:i, :e, :n, now(), 0) on conflict do nothing"),
        {"i": user_id, "e": f"worker-{user_id}@example.test", "n": "워커검사"},
    )

    made = []
    now = datetime.now(timezone.utc)
    for offset in (0, 1):          # 0 이 최신, 1 이 한 시간 전
        video = VideoOrm(
            id=uuid.uuid4(),
            user_id=user_id,
            sport_code="baseball",
            storage_key=f"videos/{user_id}/{uuid.uuid4()}.mp4",
            duration_ms=4_000,
            side=None,
            created_at=now,
        )
        job = AnalysisJobOrm(
            id=uuid.uuid4(),
            video_id=video.id,
            status=QUEUED,
            # 남의 leftover 보다 확실히 오래되게 둔다 — 위 `_ANCIENT` 주석 참고.
            created_at=_ANCIENT - timedelta(hours=offset),
        )
        # 🔴 영상을 **먼저 밀어 넣는다.** 둘을 함께 add 하면 SQLAlchemy 가
        #    타입 순서로 flush 해 `analysis_job` 이 먼저 나가고 외래키가 터진다.
        db_session.add(video)
        db_session.flush()
        db_session.add(job)
        db_session.flush()
        made.append((job.id, video.id))
    db_session.commit()

    newest, oldest = made
    yield {"oldest": oldest, "newest": newest, "user_id": user_id}

    for job_id, video_id in made:
        db_session.execute(
            text("delete from analysis_job where id = :i"), {"i": job_id}
        )
        db_session.execute(text("delete from video where id = :i"), {"i": video_id})
    db_session.execute(text('delete from "user" where id = :i'), {"i": user_id})
    db_session.commit()


def test_오래된_것부터_집는다(db_session, queued):
    claimed = JobPgRepository(_new_session()).claim_next()
    assert claimed is not None
    assert claimed.job_id == queued["oldest"][0]
    assert claimed.storage_key.startswith(f"videos/{queued['user_id']}/")
    assert claimed.sport_code == "baseball"


def test_집으면_running_과_started_at_이_찬다(db_session, queued):
    claimed = JobPgRepository(_new_session()).claim_next()
    assert claimed is not None

    db_session.expire_all()
    row = db_session.get(AnalysisJobOrm, claimed.job_id)
    assert row.status == RUNNING
    assert row.started_at is not None
    assert row.finished_at is None      # 아직 안 끝났다


def test_두_워커가_같은_작업을_집지_않는다(db_session, queued):
    """🔴 이 검사가 이 파일의 존재 이유다. 스텁으로는 절대 안 걸린다."""
    first = JobPgRepository(_new_session()).claim_next()
    second = JobPgRepository(_new_session()).claim_next()

    assert first is not None and second is not None
    assert first.job_id != second.job_id
    assert {first.job_id, second.job_id} == {
        queued["oldest"][0], queued["newest"][0]
    }


def test_잠긴_행을_건너뛰고_다음_것을_집는다(db_session, queued):
    """`SKIP LOCKED` 가 빠지면 여기서 **멈춘다** — `lock_timeout` 이 그걸 드러낸다."""
    holder = _new_session()
    # 워커 하나가 가장 오래된 행을 잠근 채 아직 커밋하지 않은 상태를 만든다.
    locked = holder.execute(
        select(AnalysisJobOrm.id)
        .where(AnalysisJobOrm.status == QUEUED)
        .order_by(AnalysisJobOrm.created_at)
        .limit(1)
        .with_for_update()
    ).scalar_one()
    assert locked == queued["oldest"][0]

    try:
        other = _new_session()
        # 🔴 멈추면 2초 뒤에 오류가 난다. 이것이 없으면 검사가 영원히 걸린다.
        other.execute(text("set local lock_timeout = '2s'"))
        claimed = JobPgRepository(other).claim_next()

        assert claimed is not None, "잠긴 행 때문에 큐가 비어 보이면 안 된다"
        assert claimed.job_id == queued["newest"][0], "잠긴 것을 집었다"
    finally:
        holder.rollback()
        holder.close()


def test_finish_는_running_일_때만_바꾼다(db_session, queued):
    job_id = queued["oldest"][0]

    # queued 인 채로 끝내려 하면 현재 상태를 돌려준다 — 라우터가 409 로 옮긴다.
    assert JobPgRepository(_new_session()).finish(job_id, "succeeded", None) == QUEUED

    claimed = JobPgRepository(_new_session()).claim_next()
    assert claimed is not None and claimed.job_id == job_id

    assert JobPgRepository(_new_session()).finish(job_id, "succeeded", None) is None

    db_session.expire_all()
    row = db_session.get(AnalysisJobOrm, job_id)
    assert row.status == "succeeded"
    assert row.finished_at is not None

    # 두 번째 보고는 막힌다. 통과시키면 finished_at 이 뒤로 밀린다.
    assert JobPgRepository(_new_session()).finish(job_id, "failed", "x") == "succeeded"


def test_없는_작업은_missing_이다(db_session):
    assert JobPgRepository(_new_session()).finish(uuid.uuid4(), "failed", None) == "missing"
