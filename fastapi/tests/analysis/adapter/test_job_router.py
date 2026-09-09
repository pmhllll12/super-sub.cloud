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
    report_key_of,
    status_of,
)
from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _OBJECTS,
    _VIDEOS,
    FakeStorage,
    put_object,
    reset_videos,
)
from app.analysis.dependencies.video_providers import get_storage_optional
from app.analysis.domain.entities.video_entity import VideoEntity
from app.core.config import settings
from app.main import app
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
            # 지정이 없으면 둘 다 null — 「자동으로 고르기」 (미결 `paik` 6번).
            "subject_box": None,
            "subject_at_ms": None,
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

    def test_지정_박스가_claim_응답에_실린다(self, client):
        """미결 `paik` 6번 — 「이 사람으로 분석」 이 워커가 읽는 자리(claim)까지 온다."""
        job_id = uuid4()
        enqueue(
            job_id, uuid4(),
            subject_box=[0.39, 0.35, 0.12, 0.4], subject_at_ms=4_200,
        )
        body = client.post(CLAIM, headers=_hdr()).json()
        assert body["subject_box"] == [0.39, 0.35, 0.12, 0.4]
        assert body["subject_at_ms"] == 4_200

    def test_지정이_없으면_null_이_온다(self, client):
        enqueue(uuid4(), uuid4())
        body = client.post(CLAIM, headers=_hdr()).json()
        assert body["subject_box"] is None and body["subject_at_ms"] is None


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

    def test_성공_보고에_리포트_자리가_실린다(self, client):
        """미결 `paik` 11번 — 워커가 만든 리포트 키를 작업에 남긴다."""
        job_id = uuid4()
        self._claim(client, job_id)
        key = "reports/u1/v1/report.json"

        res = client.patch(
            _job(job_id),
            json={"status": "succeeded", "report_key": key},
            headers=_hdr(),
        )
        assert res.status_code == 204
        assert report_key_of(job_id) == key

    def test_리포트_자리는_안_실어도_된다(self, client):
        """워커가 자리를 못 실어도 분석은 성공한 것이라 보고는 통과한다."""
        job_id = uuid4()
        self._claim(client, job_id)

        res = client.patch(
            _job(job_id), json={"status": "succeeded"}, headers=_hdr()
        )
        assert res.status_code == 204
        assert report_key_of(job_id) is None

    def test_실패_보고의_리포트_자리는_버린다(self, client):
        """🔴 실패한 작업이 리포트를 가리키면 화면이 없는 것을 읽으러 간다."""
        job_id = uuid4()
        self._claim(client, job_id)

        res = client.patch(
            _job(job_id),
            json={"status": "failed", "report_key": "reports/u1/v1/report.json"},
            headers=_hdr(),
        )
        assert res.status_code == 204
        assert report_key_of(job_id) is None

    def test_리포트_자리가_너무_길면_422_다(self, client):
        """상한은 S3 객체 키 한계(1024)다."""
        job_id = uuid4()
        self._claim(client, job_id)

        res = client.patch(
            _job(job_id),
            json={"status": "succeeded", "report_key": "r/" + "x" * 1023},
            headers=_hdr(),
        )
        assert res.status_code == 422
        assert status_of(job_id) == "running"     # 안 바뀐다

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


class TestReclaim:
    """워커가 **보고 없이 죽은** 작업을 되찾는다.

    🔴 이 경로가 없으면 GPU 인스턴스가 분석 도중 자동 종료될 때마다 작업이
    `running` 인 채 영영 남는다.
    """

    def _stall(self, job_id, minutes):
        """그 작업이 `minutes` 분 전에 시작된 것처럼 만든다."""
        from app.analysis.adapter.outbound.stub.job_stub_repository import _JOBS

        _JOBS[job_id].started_at = datetime.now(timezone.utc) - timedelta(
            minutes=minutes
        )

    def test_오래_멈춘_것을_다시_큐에_넣는다(self, client):
        stalled = uuid4()
        enqueue(stalled, uuid4())
        assert client.post(CLAIM, headers=_hdr()).status_code == 200
        assert status_of(stalled) == "running"

        self._stall(stalled, 999)

        # 다음 claim 이 회수하고, 회수된 그것을 다시 집는다.
        res = client.post(CLAIM, headers=_hdr())
        assert res.status_code == 200
        assert res.json()["job_id"] == str(stalled)
        assert "회수됨" in (failure_reason_of(stalled) or "")

    def test_아직_도는_것은_건드리지_않는다(self, client):
        """🔴 임계 시간이 짧으면 **돌고 있는 작업을 빼앗아** 두 번 분석한다."""
        running = uuid4()
        enqueue(running, uuid4())
        assert client.post(CLAIM, headers=_hdr()).status_code == 200

        # 방금 집었으니 회수 대상이 아니다 — 큐는 비어 있어야 한다.
        assert client.post(CLAIM, headers=_hdr()).status_code == 204
        assert status_of(running) == "running"
        assert failure_reason_of(running) is None

    def test_두_번째로_멈추면_실패로_끝낸다(self, client):
        """되돌리기만 하면 워커를 죽이는 클립이 큐를 영원히 돈다."""
        poison = uuid4()
        enqueue(poison, uuid4())

        assert client.post(CLAIM, headers=_hdr()).status_code == 200
        self._stall(poison, 999)                      # 1회차 사망

        assert client.post(CLAIM, headers=_hdr()).status_code == 200   # 회수 + 재집기
        self._stall(poison, 999)                      # 2회차 사망

        # 이번에는 큐로 안 돌아온다 — 실패로 끝난다.
        assert client.post(CLAIM, headers=_hdr()).status_code == 204
        assert status_of(poison) == "failed"

    def test_회수가_성공_보고를_덮지_않는다(self, client):
        """회수 표시가 남아 있어도 성공하면 사유가 비어야 한다."""
        job_id = uuid4()
        enqueue(job_id, uuid4())
        assert client.post(CLAIM, headers=_hdr()).status_code == 200
        self._stall(job_id, 999)
        assert client.post(CLAIM, headers=_hdr()).status_code == 200   # 회수 + 재집기

        assert client.patch(
            _job(job_id), json={"status": "succeeded"}, headers=_hdr()
        ).status_code == 204
        assert status_of(job_id) == "succeeded"
        assert failure_reason_of(job_id) is None


class TestProvisionalSweep:
    """claim 이 저장 안 한 오래된 임시 영상도 정리한다(미결 jin 24번 백스톱)."""

    @pytest.fixture(autouse=True)
    def _clean(self):
        reset_videos()
        app.dependency_overrides[get_storage_optional] = FakeStorage
        yield
        app.dependency_overrides.pop(get_storage_optional, None)
        reset_videos()

    def test_claim_이_오래된_미저장분을_치운다(self, client):
        user_id = uuid4()
        old = VideoEntity(
            id=uuid4(),
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{user_id}/old.mp4",
            duration_ms=5_000,
            side=None,
            kept=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        fresh = VideoEntity(
            id=uuid4(),
            user_id=user_id,
            sport_code="football",
            storage_key=f"videos/{user_id}/fresh.mp4",
            duration_ms=5_000,
            side=None,
            kept=False,
            created_at=datetime.now(timezone.utc),
        )
        _VIDEOS[old.id] = old
        _VIDEOS[fresh.id] = fresh
        put_object(old.storage_key, 1)
        put_object(f"reports/{user_id}/{old.id}/report.json", 1)

        assert client.post(CLAIM, headers=_hdr()).status_code == 204  # 큐는 비었다

        assert old.id not in _VIDEOS
        assert fresh.id in _VIDEOS
        assert old.storage_key not in _OBJECTS
        assert f"reports/{user_id}/{old.id}/report.json" not in _OBJECTS
