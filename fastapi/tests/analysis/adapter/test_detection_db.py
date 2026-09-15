"""`detect` 작업이 실제 PostgreSQL에서 안전한지 확인한다. 미결 `ho` 44번.

계약 테스트(`test_detection_router.py`·`test_job_router.py`)는 스텁을 끼우므로
JSON 컬럼(`detection_result`)이 실제로 왕복하는지, `job_type`이 진짜 컬럼으로
저장·정렬되는지는 여기서만 본다. `claim_next`의 잠금·`SKIP LOCKED` 자체는
`test_job_db.py`가 이미 지킨다 — 여기서 다시 보지 않는다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.pg.job_pg_repository import JobPgRepository
from app.analysis.domain.rules.job_rules import DETECT, QUEUED

pytestmark = pytest.mark.db

# `test_job_db.py`와 같은 이유 — 개발 DB의 큐가 비어 있지 않다.
_ANCIENT = datetime(2000, 1, 1, tzinfo=timezone.utc)


def _new_session():
    from app.core.database import engine_or_none

    engine = engine_or_none()
    if engine is None:
        pytest.skip("DATABASE_URL 이 설정되지 않았다")
    return Session(engine)


@pytest.fixture
def video(db_session):
    """영상 하나. 작업은 각 테스트가 필요한 만큼 직접 만든다."""
    user_id = uuid.uuid4()
    db_session.execute(
        text(
            'insert into "user" (id, email, nickname, created_at, token_version) '
            "values (:i, :e, :n, now(), 0) on conflict do nothing"
        ),
        {
            "i": user_id,
            "e": f"detect-{user_id}@example.test",
            # 🔴 닉네임 유일 제약(2026-09-15 추가) — 고정 문자열이면 이전 실행의
            # 잔여 행과 충돌해 `ON CONFLICT DO NOTHING`이 조용히 삼킨다.
            "n": f"검출검사{uuid.uuid4().hex[:6]}",
        },
    )
    v = VideoOrm(
        id=uuid.uuid4(),
        user_id=user_id,
        sport_code="football",
        storage_key=f"videos/{user_id}/{uuid.uuid4()}.mp4",
        duration_ms=8_000,
        side=None,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(v)
    db_session.commit()

    yield v.id

    db_session.execute(
        text("delete from analysis_job where video_id = :v"), {"v": v.id}
    )
    db_session.execute(text("delete from video where id = :i"), {"i": v.id})
    db_session.execute(text('delete from "user" where id = :i'), {"i": user_id})
    db_session.commit()


def test_create_detect_job이_실제로_적재된다(db_session, video):
    job_id = JobPgRepository(_new_session()).create_detect_job(video, at_ms=2500)

    db_session.expire_all()
    row = db_session.get(AnalysisJobOrm, job_id)
    assert row is not None
    assert row.video_id == video
    assert row.job_type == DETECT
    assert row.status == QUEUED
    assert row.subject_at_ms == 2500
    assert row.subject_box is None       # detect 는 박스가 없다


def test_get_latest_detection이_가장_최근_것을_돌려준다(db_session, video):
    older = AnalysisJobOrm(
        id=uuid.uuid4(),
        video_id=video,
        job_type=DETECT,
        status=QUEUED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        subject_at_ms=1000,
    )
    newer = AnalysisJobOrm(
        id=uuid.uuid4(),
        video_id=video,
        job_type=DETECT,
        status=QUEUED,
        created_at=datetime.now(timezone.utc),
        subject_at_ms=1500,
    )
    db_session.add(older)
    db_session.add(newer)
    db_session.commit()

    found = JobPgRepository(_new_session()).get_latest_detection(video)
    assert found is not None
    assert found.job_id == newer.id


def test_analyze_작업은_get_latest_detection에_안_걸린다(db_session, video):
    analyze_job = AnalysisJobOrm(
        id=uuid.uuid4(),
        video_id=video,
        job_type="analyze",
        status=QUEUED,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(analyze_job)
    db_session.commit()

    assert JobPgRepository(_new_session()).get_latest_detection(video) is None


def test_claim과_finish가_detect_결과를_왕복시킨다(db_session, video):
    """전체 흐름 — 큐잉 → 집기(`job_type` 보존) → 완료 보고(`detection_result` 저장)."""
    job_id = uuid.uuid4()
    db_session.add(
        AnalysisJobOrm(
            id=job_id,
            video_id=video,
            job_type=DETECT,
            status=QUEUED,
            created_at=_ANCIENT,      # 개발 DB의 다른 큐보다 확실히 오래되게
            subject_at_ms=1000,
        )
    )
    db_session.commit()

    repo = JobPgRepository(_new_session())
    claimed = repo.claim_next()
    assert claimed is not None
    assert claimed.job_id == job_id
    assert claimed.job_type == DETECT

    result = {"people": [{"box": [0.1, 0.2, 0.15, 0.4], "score": 0.87}], "ball": None}
    blocked = repo.finish(job_id, "succeeded", None, detection_result=result)
    assert blocked is None

    db_session.expire_all()
    row = db_session.get(AnalysisJobOrm, job_id)
    assert row.status == "succeeded"
    assert row.detection_result == result
    assert row.report_key is None        # detect 작업은 리포트 자리가 없다
