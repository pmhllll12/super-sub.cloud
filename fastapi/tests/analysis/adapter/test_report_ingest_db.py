"""`ReportIngestPgRepository` 를 실제 PostgreSQL 로 확인한다. 미결 `jin` 27번.

워커의 `report.json` 을 `parse_report` 로 옮긴 뒤 이 저장소가 `analysis_metric`
+ `analysis_metric_value` + `analysis_metric_criterion` + `analysis_report` 를
한 트랜잭션으로 채운다. 재분석이면 앞의 것을 덮는다.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.pg.report_ingest_pg_repository import (
    ReportIngestPgRepository,
)
from app.analysis.application.ports.output.report_ingest_port import UnknownMetricCode
from app.analysis.application.use_cases.report_parser import parse_report

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _envelope(*, sport="football", motion="instep_shot", score=71):
    return {
        "schema_version": "1.0",
        "source_video": "s3://b/videos/u/v.mp4",
        "analyzed_at": "20260910T120000Z",
        "code_version": "abc1234",
        "rubric": {"sport": sport, "motion": motion, "version": "0.1"},
        "swing_side": "right",
        "sampled_fps": 30.0,
        "frames": 300,
        "frame_metrics_seconds": {"impact_frame": 2.07},
        "judge_model": "exaone-4.0-1.2b",
        "previews": {"impact": "s3://b/reports/u/v/impact.png"},
        "keypoint_quality": {"known": True, "swing_side_valid_ratio": 0.9},
        "features": {
            "trunk_forward_lean_deg_at_impact": 12.4,
            "plant_knee_angle_at_impact": 158.0,
            "impact_frame": 62,
        },
        "result": {
            "score": score,
            "grade": "B",
            "summary": "디딤발 무릎 굽히기가 강점입니다.",
            "pipeline_version": "pose-v0.1",
            "provisional": True,
            "breakdown": [
                {
                    "criterion_id": "plant_knee_flexion",
                    "name": "디딤발 무릎 굽히기",
                    "grade": 2,
                    "weight": 0.15,
                    "contribution": 15.0,
                    "title": "흔들리지 않는 축",
                    "band": "150~170",
                    "out_of_band": "",
                    "stat": 88.5,
                    "evidence": "안정적으로 놓였습니다.",
                    "metric_ref": "plant_knee_angle_at_impact",
                },
            ],
            "skipped": [
                {"criterion_id": "plant_foot_position", "name": "디딤발 위치",
                 "weight": 0.15},
            ],
        },
    }


@pytest.fixture
def job(db_client, db_session):
    email = f"ingest-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "업로더"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    now = datetime.now(timezone.utc)
    video_id, job_id = uuid.uuid4(), uuid.uuid4()
    db_session.add(
        VideoOrm(
            id=video_id, user_id=user_id, sport_code="football",
            storage_key=f"videos/{video_id}.mp4", duration_ms=10_000,
            side="right", created_at=now,
        )
    )
    db_session.flush()
    db_session.add(
        AnalysisJobOrm(id=job_id, video_id=video_id, status="running",
                       created_at=now)
    )
    db_session.commit()

    yield {"job_id": job_id, "video_id": video_id, "user_id": user_id}

    db_session.rollback()
    for sql in (
        "delete from analysis_metric where analysis_job_id = :j",
        "delete from analysis_job where id = :j",
    ):
        db_session.execute(text(sql), {"j": str(job_id)})
    db_session.execute(text("delete from video where id = :v"),
                       {"v": str(video_id)})
    db_session.execute(text("delete from user_credential where user_id = :u"),
                       {"u": str(user_id)})
    db_session.execute(text('delete from "user" where id = :u'),
                       {"u": str(user_id)})
    db_session.commit()


def _counts(db_session, job_id):
    row = db_session.execute(
        text(
            "select "
            "  (select count(*) from analysis_metric where analysis_job_id = :j) m,"
            "  (select count(*) from analysis_metric_value v join analysis_metric am"
            "     on v.analysis_metric_id = am.id where am.analysis_job_id = :j) v,"
            "  (select count(*) from analysis_metric_criterion c join analysis_metric am"
            "     on c.analysis_metric_id = am.id where am.analysis_job_id = :j) c,"
            "  (select count(*) from analysis_report r join analysis_metric am"
            "     on r.analysis_metric_id = am.id where am.analysis_job_id = :j) r"
        ),
        {"j": str(job_id)},
    ).one()
    return {"metric": row.m, "value": row.v, "criterion": row.c, "report": row.r}


def test_리포트가_네_테이블에_적재된다(job, db_session):
    parsed = parse_report(json.dumps(_envelope()).encode())
    ok = ReportIngestPgRepository(db_session).replace_for_job(job["job_id"], parsed)
    assert ok is True

    c = _counts(db_session, job["job_id"])
    assert c["metric"] == 1
    # features 3(impact_frame 은 초 환산으로) + total_score + grade.* 1 + stat.* 1 = 6
    assert c["value"] == 6
    assert c["criterion"] == 2  # breakdown 1 + skipped 1
    assert c["report"] == 1

    report = db_session.execute(
        text(
            "select r.summary, r.provisional, r.schema_version, r.keypoint_quality,"
            "       am.rubric_sport, am.rubric_motion "
            "from analysis_report r join analysis_metric am "
            "  on r.analysis_metric_id = am.id where am.analysis_job_id = :j"
        ),
        {"j": str(job["job_id"])},
    ).one()
    assert report.provisional is True
    assert report.schema_version == "1.0"
    assert report.rubric_sport == "football" and report.rubric_motion == "instep_shot"


def test_재분석은_앞의_것을_덮는다(job, db_session):
    repo = ReportIngestPgRepository(db_session)
    repo.replace_for_job(job["job_id"], parse_report(json.dumps(_envelope(score=40)).encode()))
    repo.replace_for_job(job["job_id"], parse_report(json.dumps(_envelope(score=90)).encode()))

    c = _counts(db_session, job["job_id"])
    assert c["metric"] == 1  # 두 벌이 아니다
    total = db_session.execute(
        text(
            "select v.value from analysis_metric_value v join analysis_metric am "
            "  on v.analysis_metric_id = am.id "
            "where am.analysis_job_id = :j and v.metric_code = 'total_score'"
        ),
        {"j": str(job["job_id"])},
    ).scalar()
    assert int(total) == 90


def test_정의에_없는_지표_코드는_통째로_거부한다(job, db_session):
    """`grade.quidditch.x.y` 는 시드에 없다 — 반쯤 적재하지 않는다."""
    parsed = parse_report(json.dumps(_envelope(sport="quidditch")).encode())
    with pytest.raises(UnknownMetricCode):
        ReportIngestPgRepository(db_session).replace_for_job(job["job_id"], parsed)
    db_session.rollback()
    assert _counts(db_session, job["job_id"])["metric"] == 0


def test_작업이_없으면_False(db_session):
    parsed = parse_report(json.dumps(_envelope()).encode())
    ok = ReportIngestPgRepository(db_session).replace_for_job(uuid.uuid4(), parsed)
    assert ok is False
