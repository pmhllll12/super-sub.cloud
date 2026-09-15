"""analysis/adapter/inbound/api/v1/reference_player_router.py — 계약 문서.

스텁을 끼워 DB·S3 없이 돈다. 실제 저장·조인은 `test_reference_player_db.py`
가 본다.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.job_stub_repository import (
    StubJobRepository,
    enqueue,
    reset_jobs,
)
from app.analysis.adapter.outbound.stub.reference_player_stub_repository import (
    PLAYERS_BY_ID,
)
from app.analysis.adapter.outbound.stub.video_stub_repository import (
    StubVideoRepository,
    put_blob,
    reset_videos,
)
from app.analysis.domain.entities.video_entity import VideoEntity
from app.core.security import issue_access_token
from tests.conftest import V1, error_code
from datetime import datetime, timezone

_REPORT = {
    "schema_version": "1.4",
    "skeleton": {
        "known": True,
        "fps": 15.0,
        "frames": 3,
        "frame_size": [1920, 1080],
        "swing_leg": "right",
        "direction": 1,
        "keypoint_names": ["nose", "left_eye"],
        "moments": {"before": 0, "impact": 1, "after": 2},
        "moments_seconds": {"before": 0.0, "impact": 0.067, "after": 0.133},
        "after_clipped": False,
        # 가운데 프레임은 못 잡음 — null 이 그대로 남아야 한다.
        "joints": [[[0.1, 0.2, 0.9]], None, [[0.3, 0.4, 0.8]]],
    },
}

_REPORT_NO_SKELETON = {"schema_version": "1.1"}


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_videos()
    reset_jobs()
    yield
    reset_videos()
    reset_jobs()


class TestListReferencePlayers:
    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/reference-players").status_code == 401

    def test_시드된_두_명이_이름순으로_온다(self, client):
        res = client.get(f"{V1}/reference-players", headers=_headers(uuid4()))
        assert res.status_code == 200
        rows = res.json()
        assert {r["id"] for r in rows} == {"rovelli", "castanheira"}
        assert [r["name"] for r in rows] == sorted(r["name"] for r in rows)
        # 재생 주소가 없다 — 선수 원본 영상이 S3 에 없어서다.
        assert "src" not in rows[0] and "playback_url" not in rows[0]


class TestReferencePlayerSkeleton:
    def test_없는_선수는_404(self, client):
        res = client.get(
            f"{V1}/reference-players/ghost/skeleton", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "PLAYER_NOT_FOUND"

    def test_있는_선수는_관절이_그대로_온다(self, client):
        player = PLAYERS_BY_ID["rovelli"]
        put_blob(player.report_key, json.dumps(_REPORT).encode())

        res = client.get(
            f"{V1}/reference-players/rovelli/skeleton", headers=_headers(uuid4())
        )
        assert res.status_code == 200
        body = res.json()
        assert body["known"] is True
        assert body["frames"] == 3
        # 못 잡은 가운데 프레임이 배열에서 빠지지 않는다.
        assert body["joints"] == [[[0.1, 0.2, 0.9]], None, [[0.3, 0.4, 0.8]]]
        assert body["moments"] == {"before": 0, "impact": 1, "after": 2}

    def test_리포트에_스켈레톤이_없으면_명시적_빈_응답(self, client):
        player = PLAYERS_BY_ID["castanheira"]
        put_blob(player.report_key, json.dumps(_REPORT_NO_SKELETON).encode())

        res = client.get(
            f"{V1}/reference-players/castanheira/skeleton",
            headers=_headers(uuid4()),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["known"] is False
        assert body["why"]


class TestVideoSkeleton:
    def _video(self, user_id):
        v = VideoEntity(
            id=uuid4(),
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{user_id}/clip.mp4",
            duration_ms=8_000,
            side=None,
            created_at=datetime.now(timezone.utc),
        )
        StubVideoRepository().register(v)
        return v

    def test_남의_영상은_404(self, client):
        owner, intruder = uuid4(), uuid4()
        video = self._video(owner)

        res = client.get(
            f"{V1}/videos/{video.id}/skeleton", headers=_headers(intruder)
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_없는_영상은_404(self, client):
        res = client.get(
            f"{V1}/videos/{uuid4()}/skeleton", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_분석_실패는_ANALYSIS_FAILED(self, client):
        user_id = uuid4()
        v = VideoEntity(
            id=uuid4(),
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{user_id}/clip.mp4",
            duration_ms=8_000,
            side=None,
            created_at=datetime.now(timezone.utc),
            analysis_status="failed",
            analysis_failure_reason="사람을 못 찾았습니다.",
        )
        StubVideoRepository().register(v)

        res = client.get(f"{V1}/videos/{v.id}/skeleton", headers=_headers(user_id))
        assert res.status_code == 404
        assert error_code(res) == "ANALYSIS_FAILED"

    def test_아직_리포트가_없으면_REPORT_NOT_READY(self, client):
        user_id = uuid4()
        video = self._video(user_id)

        res = client.get(
            f"{V1}/videos/{video.id}/skeleton", headers=_headers(user_id)
        )
        assert res.status_code == 404
        assert error_code(res) == "REPORT_NOT_READY"

    def test_성공한_분석의_관절을_그대로_돌려준다(self, client):
        user_id = uuid4()
        video = self._video(user_id)
        report_key = f"reports/{user_id}/{video.id}/report.json"
        put_blob(report_key, json.dumps(_REPORT).encode())

        job_id = uuid4()
        enqueue(job_id, video.id, storage_key=video.storage_key)
        repo = StubJobRepository()
        repo.claim_next()
        assert repo.finish(job_id, "succeeded", None, report_key) is None

        res = client.get(
            f"{V1}/videos/{video.id}/skeleton", headers=_headers(user_id)
        )
        assert res.status_code == 200
        body = res.json()
        assert body["known"] is True
        assert body["joints"][1] is None  # 못 잡은 프레임이 안 빠졌다
