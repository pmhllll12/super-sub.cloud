"""`GET /reference-players`·`/skeleton`·`/videos/{id}/skeleton`이 실제
PostgreSQL에서 도는지 확인한다. `paik` 29번.

계약 테스트(`test_reference_player_router.py`)는 스텁을 끼우므로, `reference_
player` 시드(마이그레이션)가 실제로 들어가 있는지, 등록이 만든 진짜
`analysis_job` 행에서 `report_key`를 제대로 찾아오는지는 여기서만 본다.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.analysis.adapter.outbound.stub.video_stub_repository import (
    FakeStorage,
    put_blob,
    put_object,
    reset_videos,
)
from app.analysis.dependencies.video_providers import get_storage
from app.main import app
from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"
SIZE_OK = 50 * 1024 * 1024

_REPORT = {
    "schema_version": "1.4",
    "skeleton": {
        "known": True,
        "fps": 15.0,
        "frames": 3,
        "frame_size": [1920, 1080],
        "swing_leg": "right",
        "moments": {"before": 0, "impact": 1, "after": 2},
        "joints": [[[0.1, 0.2, 0.9]], None, [[0.3, 0.4, 0.8]]],
    },
}


@pytest.fixture(autouse=True)
def _fake_storage():
    """저장소만 가짜로 바꾼다. **DB는 진짜다** — `test_video_db.py`와 같은 이유."""
    app.dependency_overrides[get_storage] = FakeStorage
    reset_videos()
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_storage, None)
        reset_videos()


def _account(db_client):
    nickname = f"관절검사{uuid.uuid4().hex[:6]}"
    email = f"skeleton-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _register_video(db_client, account, db_session):
    """등록한 영상을 이 함수가 스스로 치운다 — 개발 DB의 `analysis_job` 큐에
    안 지워진 행이 쌓이면(`test_job_db.py` 머리말이 이미 경고한 문제) 다른
    파일의 동시성 검사(`reclaim_stale` 등, 테이블 전체를 훑는다)가 흔들린다.
    """
    up = db_client.post(
        f"{V1}/videos/upload-url",
        json={"content_type": "video/mp4", "size_bytes": SIZE_OK, "filename": "c.mp4"},
        headers=account["headers"],
    )
    key = up.json()["storage_key"]
    put_object(key, SIZE_OK)
    res = db_client.post(
        f"{V1}/videos",
        json={
            "sport_code": "football",
            "storage_key": key,
            "duration_ms": 10_000,
            "width": 1920,
            "height": 1080,
        },
        headers=account["headers"],
    )
    assert res.status_code == 201, res.text
    video_id = uuid.UUID(res.json()["id"])

    def _cleanup():
        db_session.execute(
            text("DELETE FROM analysis_job WHERE video_id = :v"), {"v": video_id}
        )
        db_session.execute(
            text("DELETE FROM video_validation WHERE video_id = :v"), {"v": video_id}
        )
        db_session.execute(text("DELETE FROM video WHERE id = :v"), {"v": video_id})
        db_session.commit()

    _CLEANUPS.append(_cleanup)
    return video_id


_CLEANUPS: list = []


@pytest.fixture(autouse=True)
def _cleanup_videos():
    _CLEANUPS.clear()
    yield
    for cleanup in _CLEANUPS:
        cleanup()
    _CLEANUPS.clear()


class TestReferencePlayers:
    def test_시드가_실제로_두_명_들어있다(self, db_client, db_session):
        rows = db_session.execute(
            text("SELECT id, name, report_key FROM reference_player ORDER BY id")
        ).all()
        assert {r[0] for r in rows} == {"rovelli", "castanheira"}
        for row in rows:
            assert row[2].startswith("reports/pro/")

    def test_시드된_선수의_리포트를_읽는다(self, db_client):
        account = _account(db_client)
        put_blob(
            "reports/pro/pexels-15436954/report.json", json.dumps(_REPORT).encode()
        )

        res = db_client.get(
            f"{V1}/reference-players/rovelli/skeleton", headers=account["headers"]
        )
        assert res.status_code == 200, res.text
        assert res.json()["frames"] == 3


class TestVideoSkeletonDb:
    def test_실제_등록된_영상의_분석이_끝나면_관절을_읽는다(
        self, db_client, db_session
    ):
        account = _account(db_client)
        video_id = _register_video(db_client, account, db_session)

        report_key = f"reports/{account['id']}/{video_id}/report.json"
        put_blob(report_key, json.dumps(_REPORT).encode())

        # 등록이 이미 analyze 작업(queued)을 만들어 뒀다 — 워커가 끝낸 것처럼
        # 직접 succeeded로 옮긴다(워커 claim/finish 흐름 자체는
        # test_job_db.py가 이미 지킨다, 여기서는 읽는 경로만 본다).
        db_session.execute(
            text(
                "UPDATE analysis_job SET status = 'succeeded', report_key = :k, "
                "finished_at = now() WHERE video_id = :v"
            ),
            {"k": report_key, "v": video_id},
        )
        db_session.commit()

        res = db_client.get(
            f"{V1}/videos/{video_id}/skeleton", headers=account["headers"]
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["known"] is True
        assert body["joints"][1] is None

    def test_아직_분석_전이면_REPORT_NOT_READY(self, db_client, db_session):
        account = _account(db_client)
        video_id = _register_video(db_client, account, db_session)

        res = db_client.get(
            f"{V1}/videos/{video_id}/skeleton", headers=account["headers"]
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "REPORT_NOT_READY"

    def test_남의_영상은_404(self, db_client, db_session):
        owner = _account(db_client)
        video_id = _register_video(db_client, owner, db_session)
        intruder = _account(db_client)

        res = db_client.get(
            f"{V1}/videos/{video_id}/skeleton", headers=intruder["headers"]
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "VIDEO_NOT_FOUND"
