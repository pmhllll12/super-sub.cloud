"""`GET /videos/{id}/report` 를 실제 PostgreSQL 로 확인한다. 미결 `jin` 27번 · `paik` 7번.

적재(`ReportIngestPgRepository`)가 채운 네 테이블을 읽기 경로가 한 뷰로 조립하는지,
허용목록 밖(총점·`band`·`stat`·가중치)이 새지 않는지 본다. 조립 SQL 자체의
조인은 여기서만 도는 코드다 — 스텁으로는 확인이 안 된다.
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
from app.analysis.application.use_cases.report_parser import parse_report
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _envelope(*, score=71):
    return {
        "schema_version": "1.0",
        "source_video": "s3://b/videos/u/v.mp4",
        "analyzed_at": "20260910T120000Z",
        "code_version": "abc1234",
        "rubric": {"sport": "football", "motion": "instep_shot", "version": "0.1"},
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
def owned(db_client, db_session):
    email = f"report-read-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "업로더"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

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

    yield {"headers": headers, "user_id": user_id,
           "video_id": video_id, "job_id": job_id}

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


def _ingest(db_session, job_id, **kw):
    parsed = parse_report(json.dumps(_envelope(**kw)).encode())
    ReportIngestPgRepository(db_session).replace_for_job(job_id, parsed)


def test_적재된_네_테이블을_한_뷰로_조립한다(db_client, db_session, owned):
    _ingest(db_session, owned["job_id"])

    res = db_client.get(
        f"{V1}/videos/{owned['video_id']}/report", headers=owned["headers"]
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["video_id"] == str(owned["video_id"])
    assert body["summary"].startswith("디딤발")
    assert body["provisional"] is True
    assert body["previews"] == {"impact": "s3://b/reports/u/v/impact.png"}
    assert body["keypoint_quality"]["known"] is True

    # 오버롤 — 영상 하나에 하나(`ho` 28번).
    assert body["total_score"] == pytest.approx(71)
    assert body["overall_grade"] == "B"

    # breakdown: 채점 1 + 제외 1, 제외가 뒤로.
    assert [c["criterion_id"] for c in body["breakdown"]] == [
        "plant_knee_flexion",
        "plant_foot_position",
    ]
    assert body["breakdown"][0]["grade"] == 2
    assert body["breakdown"][0]["evidence"].startswith("안정적")
    assert body["breakdown"][0]["stat"] == pytest.approx(88.5)
    assert body["breakdown"][1]["skipped"] is True
    assert body["breakdown"][1]["grade"] is None
    assert body["breakdown"][1]["stat"] is None  # 제외 항목은 축도 없다.

    # scenes: 프레임 지표의 초 환산만.
    assert len(body["scenes"]) == 1
    assert body["scenes"][0]["metric_code"] == "impact_frame"
    assert body["scenes"][0]["at_seconds"] == pytest.approx(2.07)

    # 허용목록 밖은 여전히 안 나온다 — `stat`·`total_score`·`overall_grade`
    # 만 새로 열렸다(`ho` 28번), 나머지는 그대로 막혀 있다.
    assert "band" not in body["breakdown"][0]
    assert "weight" not in body["breakdown"][0]
    assert "contribution" not in body["breakdown"][0]


def test_재분석이면_최신_리포트를_보여준다(db_client, db_session, owned):
    _ingest(db_session, owned["job_id"], score=40)
    _ingest(db_session, owned["job_id"], score=90)

    res = db_client.get(
        f"{V1}/videos/{owned['video_id']}/report", headers=owned["headers"]
    )
    assert res.status_code == 200, res.text
    body = res.json()
    # 한 벌만 남는다(적재가 덮으므로) — breakdown 이 두 배가 아니다.
    assert len(body["breakdown"]) == 2
    # total_score 도 최신 것 — 옛 값(40)이 아니라 덮은 값(90).
    assert body["total_score"] == pytest.approx(90)


def test_적재_전이면_404_REPORT_NOT_READY(db_client, owned):
    res = db_client.get(
        f"{V1}/videos/{owned['video_id']}/report", headers=owned["headers"]
    )
    assert res.status_code == 404
    assert error_code(res) == "REPORT_NOT_READY"


def test_남의_영상이면_404_VIDEO_NOT_FOUND(db_client, db_session, owned):
    _ingest(db_session, owned["job_id"])
    other_email = f"other-{uuid.uuid4().hex[:12]}@super-sub.example"
    db_client.post(
        f"{V1}/auth/signup",
        json={"email": other_email, "password": PASSWORD, "nickname": "남"},
    )
    login = db_client.post(
        f"{V1}/auth/login", json={"email": other_email, "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = db_client.get(
        f"{V1}/videos/{owned['video_id']}/report", headers=headers
    )
    assert res.status_code == 404
    assert error_code(res) == "VIDEO_NOT_FOUND"

    db_session.execute(
        text('delete from user_credential where user_id in '
             '(select id from "user" where email = :e)'),
        {"e": other_email},
    )
    db_session.execute(text('delete from "user" where email = :e'),
                       {"e": other_email})
    db_session.commit()
