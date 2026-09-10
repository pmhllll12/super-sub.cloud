"""`analysis_metric_criterion` 과 `analysis_report` 의 새 컬럼이 **DB 에 실재하는지**
실제 PostgreSQL 로 확인한다. 미결 `jin` 27번.

정상호 쪽 적재 코드가 이 자리에 `result.breakdown[]`·`result.skipped[]` 를 넣는다.
표에 적힌 것과 DB 에 걸린 것은 다르므로, 여기서 실제로 넣어 보고 제약을 위반해 본다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.analysis_metric_criterion_orm import (
    AnalysisMetricCriterionOrm,
)
from app.analysis.adapter.outbound.orm.analysis_metric_orm import AnalysisMetricOrm
from app.analysis.adapter.outbound.orm.analysis_report_orm import AnalysisReportOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


@pytest.fixture
def metric(db_client, db_session):
    """업로더 → 영상 → 작업 → 지표 묶음. 항목 행을 매달 자리."""
    email = f"criterion-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "업로더"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    now = datetime.now(timezone.utc)
    video_id, job_id, metric_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    db_session.add(
        VideoOrm(
            id=video_id,
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{video_id}.mp4",
            duration_ms=10_200,
            side="right",
            created_at=now,
        )
    )
    db_session.flush()
    db_session.add(
        AnalysisJobOrm(
            id=job_id, video_id=video_id, status="succeeded", created_at=now
        )
    )
    db_session.flush()
    db_session.add(
        AnalysisMetricOrm(
            id=metric_id,
            analysis_job_id=job_id,
            pipeline_version="pose-v0.1",
            rubric_sport="football",
            rubric_motion="instep_shot",
            rubric_version="0.1",
            created_at=now,
        )
    )
    db_session.commit()

    yield {"metric_id": metric_id, "job_id": job_id, "video_id": video_id,
           "user_id": user_id, "now": now}

    db_session.rollback()
    for sql, params in (
        ("delete from analysis_metric_criterion where analysis_metric_id = :m",
         {"m": str(metric_id)}),
        ("delete from analysis_report where analysis_metric_id = :m",
         {"m": str(metric_id)}),
        ("delete from analysis_metric where id = :m", {"m": str(metric_id)}),
        ("delete from analysis_job where id = :j", {"j": str(job_id)}),
        ("delete from video where id = :v", {"v": str(video_id)}),
        ("delete from user_credential where user_id = :u", {"u": str(user_id)}),
        ('delete from "user" where id = :u', {"u": str(user_id)}),
    ):
        db_session.execute(text(sql), params)
    db_session.commit()


def test_breakdown_항목이_전부_적재된다(metric, db_session):
    db_session.add(
        AnalysisMetricCriterionOrm(
            id=uuid.uuid4(),
            analysis_metric_id=metric["metric_id"],
            criterion_id="plant_knee_flexion",
            name="디딤발 무릎 굽히기",
            grade=2,
            weight=Decimal("0.1500"),
            contribution=Decimal("15.00"),
            title="흔들리지 않는 축",
            band="150~170",
            out_of_band="",
            evidence="디딤발이 공 옆에 안정적으로 놓였습니다.",
            metric_ref="plant_knee_angle_at_impact",
            skipped=False,
        )
    )
    db_session.commit()

    row = (
        db_session.query(AnalysisMetricCriterionOrm)
        .filter_by(analysis_metric_id=metric["metric_id"])
        .one()
    )
    assert row.grade == 2
    assert row.title == "흔들리지 않는 축"
    assert row.band == "150~170"
    assert row.evidence.startswith("디딤발")
    assert row.metric_ref == "plant_knee_angle_at_impact"
    assert row.skipped is False


def test_skipped_항목은_grade_title_evidence_가_NULL_이다(metric, db_session):
    """🔴 없음이 곧 「제외」다 — 0 으로 채우면 촬영 조건으로 선수를 감점하는 것."""
    db_session.add(
        AnalysisMetricCriterionOrm(
            id=uuid.uuid4(),
            analysis_metric_id=metric["metric_id"],
            criterion_id="contact_point",
            name="공 맞는 지점",
            grade=None,
            weight=Decimal("0.2000"),  # 루브릭 원값 (재정규화 전)
            contribution=None,
            title=None,
            band=None,
            out_of_band="",
            evidence=None,
            metric_ref=None,
            skipped=True,
        )
    )
    db_session.commit()

    row = (
        db_session.query(AnalysisMetricCriterionOrm)
        .filter_by(criterion_id="contact_point")
        .one()
    )
    assert row.skipped is True
    assert row.grade is None and row.title is None and row.evidence is None


def test_같은_항목을_두_번_넣으면_막힌다(metric, db_session):
    for _ in range(2):
        db_session.add(
            AnalysisMetricCriterionOrm(
                id=uuid.uuid4(),
                analysis_metric_id=metric["metric_id"],
                criterion_id="trunk_lean",
                name="상체 기울기",
                grade=1,
                weight=Decimal("0.2000"),
                out_of_band="",
            )
        )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_지표_묶음을_지우면_항목이_함께_지워진다(metric, db_session):
    """SEC-006 삭제 연쇄 — `analysis_metric` 이 사라지면 항목도 사라진다."""
    db_session.add(
        AnalysisMetricCriterionOrm(
            id=uuid.uuid4(),
            analysis_metric_id=metric["metric_id"],
            criterion_id="follow_through",
            name="차고 난 뒤 마무리",
            grade=0,
            weight=Decimal("0.1000"),
            out_of_band="구간 위",
        )
    )
    db_session.commit()

    db_session.execute(
        text("delete from analysis_metric where id = :m"),
        {"m": str(metric["metric_id"])},
    )
    db_session.commit()

    left = db_session.execute(
        text(
            "select count(*) from analysis_metric_criterion "
            "where analysis_metric_id = :m"
        ),
        {"m": str(metric["metric_id"])},
    ).scalar()
    assert left == 0


def test_analysis_report_의_새_컬럼이_JSON_왕복한다(metric, db_session):
    previews = {"impact": "s3://b/reports/x/impact.png", "tracked": "s3://b/reports/x/t.mp4"}
    kq = {
        "known": True,
        "limb": "leg",
        "side": "auto",
        "swing_side_valid_ratio": 0.94,
        "gate_joints": 3,
        "threshold": 0.7,
        "min_keypoint_confidence": 0.3,
    }
    db_session.add(
        AnalysisReportOrm(
            id=uuid.uuid4(),
            analysis_metric_id=metric["metric_id"],
            summary="디딤발이 공보다 앞서 있습니다.",
            model_name="exaone-4.0-1.2b",
            schema_version="1.0",
            provisional=True,
            previews=previews,
            keypoint_quality=kq,
            created_at=metric["now"],
        )
    )
    db_session.commit()
    db_session.expire_all()

    row = (
        db_session.query(AnalysisReportOrm)
        .filter_by(analysis_metric_id=metric["metric_id"])
        .one()
    )
    assert row.schema_version == "1.0"
    assert row.provisional is True
    assert row.previews["impact"].endswith("impact.png")
    assert row.keypoint_quality["swing_side_valid_ratio"] == 0.94
