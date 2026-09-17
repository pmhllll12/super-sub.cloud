"""analysis/adapter/inbound/api/v1/video_router.py — `POST`/`GET /videos/{id}/detect`.

미결 `ho` 44번(검출된 사람 목록을 화면에 주는 경로) — 안 (가). 스텁을 끼워
DB 없이 돈다. **실제 큐 적재·폴링은 `test_detection_db.py`가 진짜
PostgreSQL로 본다.** 여기서는 상태 코드·에러 `code`·응답 형태만 본다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.job_stub_repository import (
    enqueue,
    reset_jobs,
)
from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _VIDEOS,
    reset_videos,
)
from app.analysis.domain.entities.video_entity import VideoEntity
from app.core.security import issue_access_token
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_videos()
    reset_jobs()
    yield
    reset_videos()
    reset_jobs()


def _video(user_id, **overrides):
    v = VideoEntity(
        id=uuid4(),
        user_id=user_id,
        sport_code="football",
        storage_key=f"videos/{user_id}/clip.mp4",
        duration_ms=10_000,
        side="right",
        created_at=datetime.now(timezone.utc),
        **overrides,
    )
    _VIDEOS[v.id] = v
    return v


class TestRequestDetection:
    def test_요청하면_202와_함께_큐잉된다(self, client):
        user_id = uuid4()
        video = _video(user_id)

        res = client.post(
            f"{V1}/videos/{video.id}/detect", headers=_headers(user_id)
        )

        assert res.status_code == 202, res.text
        body = res.json()
        assert body["status"] == "queued"
        assert body["detection_result"] is None
        assert body["failure_reason"] is None
        assert "job_id" in body

    def test_at_ms를_안_주면_기본값_1000이다(self, client):
        """`worker-interface.md`의 `at_ms` 예시(1000ms)를 그대로 따른다."""
        user_id = uuid4()
        video = _video(user_id)

        res = client.post(
            f"{V1}/videos/{video.id}/detect",
            headers=_headers(user_id),
            json={},
        )
        assert res.status_code == 202, res.text

    def test_남의_영상은_404다(self, client):
        owner, stranger = uuid4(), uuid4()
        video = _video(owner)

        res = client.post(
            f"{V1}/videos/{video.id}/detect", headers=_headers(stranger)
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_없는_영상은_404다(self, client):
        res = client.post(
            f"{V1}/videos/{uuid4()}/detect", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_로그인_없이는_401이다(self, client):
        res = client.post(f"{V1}/videos/{uuid4()}/detect")
        assert res.status_code == 401


class TestReadDetection:
    def test_요청_이력이_없으면_404다(self, client):
        user_id = uuid4()
        video = _video(user_id)

        res = client.get(f"{V1}/videos/{video.id}/detect", headers=_headers(user_id))
        assert res.status_code == 404
        assert error_code(res) == "DETECTION_NOT_FOUND"

    def test_대기중이면_상태만_온다(self, client):
        user_id = uuid4()
        video = _video(user_id)
        job_id = uuid4()
        enqueue(job_id, video.id, job_type="detect")

        res = client.get(f"{V1}/videos/{video.id}/detect", headers=_headers(user_id))
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["job_id"] == str(job_id)
        assert body["status"] == "queued"
        assert body["detection_result"] is None

    def test_남의_영상은_404다(self, client):
        owner, stranger = uuid4(), uuid4()
        video = _video(owner)
        enqueue(uuid4(), video.id, job_type="detect")

        res = client.get(f"{V1}/videos/{video.id}/detect", headers=_headers(stranger))
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_가장_최근_것만_돌려준다(self, client):
        """호출마다 새 작업을 만드는 정책 — 폴링은 최신 것만 봐야 한다."""
        from datetime import timedelta

        user_id = uuid4()
        video = _video(user_id)
        older, newer = uuid4(), uuid4()
        base = datetime.now(timezone.utc)
        enqueue(older, video.id, job_type="detect", created_at=base - timedelta(minutes=5))
        enqueue(newer, video.id, job_type="detect", created_at=base)

        res = client.get(f"{V1}/videos/{video.id}/detect", headers=_headers(user_id))
        assert res.json()["job_id"] == str(newer)
