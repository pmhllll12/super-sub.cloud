"""`/internal/analysis-jobs/*` — 워커가 큐를 소비하는 경로. 계약 3-8절.

스텁을 끼워 DB 없이 돈다. **동시성은 여기서 검증되지 않는다** — 두 워커가 같은
작업을 집지 않는지는 진짜 PostgreSQL 이라야 확인되고 `test_job_db.py` 가 본다.

## 이 검사가 보는 것

미결 `ho` 17번의 골격이다. 셋을 지킨다.

1. **기계 자격이 없으면 못 들어온다** — 사람 토큰으로도 안 된다
2. `WORKER_TOKEN` 이 비면 **아무도** 못 들어온다 (fail-closed)
3. **집은 것만 끝낼 수 있다** — `queued` 를 바로 끝내면 `started_at` 이 빈 채
   `finished_at` 만 차서 PER-001 이 보려는 값이 망가진다
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.job_stub_repository import (
    enqueue,
    failure_reason_of,
    status_of,
)
from app.core.config import settings
from tests.conftest import V1, error_code

CLAIM = f"{V1}/internal/analysis-jobs/claim"
TOKEN = "test-only-worker-token"


def _job(job_id):
    return f"{V1}/internal/analysis-jobs/{job_id}"


@pytest.fixture(autouse=True)
def _worker_token():
    """`settings` 는 전역이라 반드시 되돌린다 (`fastapi/CLAUDE.md`)."""
    before = settings.worker_token
    settings.worker_token = TOKEN
    try:
        yield
    finally:
        settings.worker_token = before


def _hdr(token=TOKEN):
    return {"X-Worker-Token": token}


class TestAuth:
    def test_자격이_없으면_401_이다(self, client):
        res = client.post(CLAIM)
        assert res.status_code == 401
        assert error_code(res) == "INVALID_TOKEN"

    def test_틀린_자격은_401_이다(self, client):
        res = client.post(CLAIM, headers=_hdr("wrong-token"))
        assert res.status_code == 401

    def test_사람_토큰으로는_못_들어온다(self, client, auth):
        """워커 경로는 사용자 인증과 **다른 축**이다."""
        assert client.post(CLAIM, headers=auth).status_code == 401

    def test_설정이_비면_맞는_토큰도_401_이다(self, client):
        """🔴 fail-closed. 값을 안 넣은 배포에서 큐가 열려 있으면 안 된다."""
        settings.worker_token = ""
        res = client.post(CLAIM, headers=_hdr())
        assert res.status_code == 401

    def test_완료_보고도_자격이_필요하다(self, client):
        res = client.patch(_job(uuid4()), json={"status": "succeeded"})
        assert res.status_code == 401


class TestClaim:
    def test_큐가_비면_204_다(self, client):
        """**오류가 아니다.** 오류로 두면 워커 로그가 빈 폴링으로 찬다."""
        res = client.post(CLAIM, headers=_hdr())
        assert res.status_code == 204

    def test_하나_집으면_워커가_알아야_할_것이_온다(self, client):
        job_id, video_id = uuid4(), uuid4()
        enqueue(
            job_id,
            video_id,
            storage_key="videos/abc/clip.mp4",
            sport_code="baseball",
            side="right",
            duration_ms=4_200,
        )

        res = client.post(CLAIM, headers=_hdr())
        assert res.status_code == 200, res.text
        body = res.json()
        assert body == {
            "job_id": str(job_id),
            "video_id": str(video_id),
            "storage_key": "videos/abc/clip.mp4",
            "sport_code": "baseball",
            "side": "right",
            "duration_ms": 4_200,
        }

    def test_집으면_running_이_된다(self, client):
        job_id = uuid4()
        enqueue(job_id, uuid4())
        assert client.post(CLAIM, headers=_hdr()).status_code == 200
        assert status_of(job_id) == "running"

    def test_같은_작업을_두_번_집지_않는다(self, client):
        enqueue(uuid4(), uuid4())
        assert client.post(CLAIM, headers=_hdr()).status_code == 200
        # 큐에 하나뿐이었으므로 두 번째는 비어 있어야 한다.
        assert client.post(CLAIM, headers=_hdr()).status_code == 204

    def test_오래된_것부터_준다(self, client):
        old, new = uuid4(), uuid4()
        base = datetime.now(timezone.utc)
        enqueue(new, uuid4(), created_at=base)
        enqueue(old, uuid4(), created_at=base - timedelta(hours=1))

        res = client.post(CLAIM, headers=_hdr())
        assert res.json()["job_id"] == str(old)


class TestFinish:
    def _claim(self, client, job_id):
        enqueue(job_id, uuid4())
        assert client.post(CLAIM, headers=_hdr()).status_code == 200

    def test_성공을_보고한다(self, client):
        job_id = uuid4()
        self._claim(client, job_id)

        res = client.patch(_job(job_id), json={"status": "succeeded"}, headers=_hdr())
        assert res.status_code == 204
        assert status_of(job_id) == "succeeded"

    def test_실패는_사유와_함께_남는다(self, client):
        job_id = uuid4()
        self._claim(client, job_id)

        res = client.patch(
            _job(job_id),
            json={"status": "failed", "failure_reason": "품질 게이트 미달"},
            headers=_hdr(),
        )
        assert res.status_code == 204
        assert status_of(job_id) == "failed"
        assert failure_reason_of(job_id) == "품질 게이트 미달"

    def test_집지_않은_작업은_409_다(self, client):
        """`queued` 를 바로 끝내면 `started_at` 이 빈 채 `finished_at` 만 찬다."""
        job_id = uuid4()
        enqueue(job_id, uuid4())

        res = client.patch(_job(job_id), json={"status": "succeeded"}, headers=_hdr())
        assert res.status_code == 409
        assert error_code(res) == "JOB_NOT_RUNNING"
        assert status_of(job_id) == "queued"

    def test_두_번_보고하면_409_다(self, client):
        """재시도가 `finished_at` 을 뒤로 밀면 소요 시간이 늘어난 것처럼 보인다."""
        job_id = uuid4()
        self._claim(client, job_id)
        assert client.patch(
            _job(job_id), json={"status": "succeeded"}, headers=_hdr()
        ).status_code == 204

        res = client.patch(_job(job_id), json={"status": "failed"}, headers=_hdr())
        assert res.status_code == 409
        assert status_of(job_id) == "succeeded"   # 첫 보고가 남는다

    def test_없는_작업은_404_다(self, client):
        res = client.patch(_job(uuid4()), json={"status": "succeeded"}, headers=_hdr())
        assert res.status_code == 404
        assert error_code(res) == "JOB_NOT_FOUND"

    @pytest.mark.parametrize("bad", ["queued", "running", "done", ""])
    def test_끝난_상태만_보고할_수_있다(self, client, bad):
        job_id = uuid4()
        self._claim(client, job_id)

        res = client.patch(_job(job_id), json={"status": bad}, headers=_hdr())
        assert res.status_code == 422
        assert status_of(job_id) == "running"     # 안 바뀐다
