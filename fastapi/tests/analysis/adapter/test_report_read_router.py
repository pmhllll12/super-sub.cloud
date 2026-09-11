"""analysis/adapter/inbound/api/v1/video_router.py — `GET /videos/{id}/report`.

미결 `jin` 27번 · `paik` 7번. 스텁을 끼워 DB 없이 돈다 — 실제 조립은
`test_report_read_db.py` 가 진짜 PostgreSQL 로 본다. 여기서는 상태 코드·에러
`code`·응답 형태(허용목록)만 본다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _VIDEOS,
    reset_report_views,
    reset_videos,
    set_report_view,
)
from app.analysis.application.dtos.report_view_dto import (
    ReportCriterionView,
    ReportSceneView,
    ReportView,
)
from app.analysis.domain.entities.video_entity import VideoEntity
from app.core.security import issue_access_token
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_videos()
    reset_report_views()
    yield
    reset_videos()
    reset_report_views()


def _video(user_id):
    v = VideoEntity(
        id=uuid4(),
        user_id=user_id,
        sport_code="football",
        storage_key=f"videos/{user_id}/clip.mp4",
        duration_ms=10_000,
        side="right",
        created_at=datetime.now(timezone.utc),
    )
    _VIDEOS[v.id] = v
    return v


def _view(video_id):
    return ReportView(
        video_id=video_id,
        analyzed_at=datetime.now(timezone.utc),
        summary="디딤발 무릎 굽히기가 강점입니다.",
        provisional=True,
        total_score=71.0,
        overall_grade="B",
        breakdown=[
            ReportCriterionView(
                criterion_id="plant_knee_flexion",
                name="디딤발 무릎 굽히기",
                grade=2,
                title="흔들리지 않는 축",
                evidence="안정적으로 놓였습니다.",
                metric_ref="plant_knee_angle_at_impact",
                skipped=False,
                stat=88.5,
            ),
            ReportCriterionView(
                criterion_id="plant_foot_position",
                name="디딤발 위치",
                grade=None,
                title=None,
                evidence=None,
                metric_ref=None,
                skipped=True,
                stat=None,
            ),
        ],
        scenes=[
            ReportSceneView(
                metric_code="impact_frame", label="임팩트 프레임", at_seconds=2.07
            )
        ],
        previews={"impact": "https://storage.invalid/get/reports/u/v/impact.png"},
        keypoint_quality={"known": True, "swing_side_valid_ratio": 0.9},
    )


def test_적재된_리포트를_돌려준다(client):
    user_id = uuid4()
    video = _video(user_id)
    set_report_view(video.id, _view(video.id))

    res = client.get(f"{V1}/videos/{video.id}/report", headers=_headers(user_id))

    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == {
        "video_id",
        "analyzed_at",
        "summary",
        "provisional",
        "total_score",
        "overall_grade",
        "breakdown",
        "scenes",
        "previews",
        "keypoint_quality",
    }
    assert body["summary"].startswith("디딤발")
    assert body["provisional"] is True
    assert body["total_score"] == pytest.approx(71.0)
    assert body["overall_grade"] == "B"
    assert len(body["breakdown"]) == 2
    assert body["breakdown"][0]["stat"] == pytest.approx(88.5)
    assert body["breakdown"][1]["skipped"] is True
    assert body["breakdown"][1]["grade"] is None
    assert body["breakdown"][1]["stat"] is None
    assert body["scenes"][0]["at_seconds"] == pytest.approx(2.07)
    # 허용목록(`ho` 28번으로 갱신): band·weight·contribution 은 여전히 안 나간다
    # — `stat`·`total_score`·`overall_grade` 는 이제 나간다(위에서 확인).
    assert "band" not in body["breakdown"][0]
    assert "weight" not in body["breakdown"][0]
    assert "contribution" not in body["breakdown"][0]


def test_없는_영상은_404_VIDEO_NOT_FOUND(client):
    user_id = uuid4()
    res = client.get(f"{V1}/videos/{uuid4()}/report", headers=_headers(user_id))
    assert res.status_code == 404
    assert error_code(res) == "VIDEO_NOT_FOUND"


def test_남의_영상은_404_VIDEO_NOT_FOUND(client):
    owner, intruder = uuid4(), uuid4()
    video = _video(owner)
    set_report_view(video.id, _view(video.id))  # 적재는 돼 있어도

    res = client.get(
        f"{V1}/videos/{video.id}/report", headers=_headers(intruder)
    )
    assert res.status_code == 404
    assert error_code(res) == "VIDEO_NOT_FOUND"


def test_영상은_있지만_적재_전이면_404_REPORT_NOT_READY(client):
    user_id = uuid4()
    video = _video(user_id)  # 뷰는 안 넣는다

    res = client.get(
        f"{V1}/videos/{video.id}/report", headers=_headers(user_id)
    )
    assert res.status_code == 404
    assert error_code(res) == "REPORT_NOT_READY"


def test_인증이_없으면_401(client):
    res = client.get(f"{V1}/videos/{uuid4()}/report")
    assert res.status_code == 401
