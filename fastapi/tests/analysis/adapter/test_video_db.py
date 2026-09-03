"""업로드 경로가 **실제 PostgreSQL 에서** 도는지 확인한다.

계약 테스트(`test_video_router.py`)는 스텁을 끼우므로 조인·외래키·삭제 연쇄를
보지 못한다. 여기서 보는 것은 셋이다.

1. 등록 한 번에 `video`·`video_validation`·`analysis_job` 이 **함께** 생긴다
2. `video_validation.video_id` 의 유일 제약이 **DB 에 실재한다**(부록 D.7)
3. 영상을 지우면 판정도 따라 지워진다(SEC-006 의 연쇄)

🔴 그리고 **`sport` 를 원시 쿼리로 읽는 자리**가 여기 걸린다. 저쪽 컬럼 이름이
바뀌면 파이썬이 잡아 주지 않으므로 이 검사가 유일한 방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.analysis.adapter.outbound.orm.video_validation_orm import VideoValidationOrm
from app.analysis.adapter.outbound.stub.video_stub_repository import (
    FakeStorage,
    put_object,
    reset_videos,
)
from app.analysis.dependencies.video_providers import get_storage
from app.main import app
from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"
SIZE_OK = 50 * 1024 * 1024


@pytest.fixture(autouse=True)
def _fake_storage():
    """저장소만 가짜로 바꾼다. **DB 는 진짜다.**

    S3 를 실제로 부르면 검사가 자격증명과 망에 묶인다 — 여기서 보려는 것은
    저장이지 업로드가 아니다.
    """
    app.dependency_overrides[get_storage] = FakeStorage
    reset_videos()
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_storage, None)
        reset_videos()


@pytest.fixture
def uploader(db_client):
    """가입한 사용자와 그 토큰. 시드 데이터에 기대지 않는다."""
    email = f"video-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "업로더"},
    )
    assert signup.status_code == 201, signup.text

    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return {
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _upload(db_client, uploader, size_bytes=SIZE_OK):
    res = db_client.post(
        f"{V1}/videos/upload-url",
        json={"content_type": "video/mp4", "size_bytes": SIZE_OK},
        headers=uploader["headers"],
    )
    assert res.status_code == 200, res.text
    key = res.json()["storage_key"]
    put_object(key, size_bytes)
    return key


def _register(db_client, uploader, key, **kw):
    body = {
        "sport_code": "football",
        "storage_key": key,
        "duration_ms": 10_000,
        "width": 1920,
        "height": 1080,
    }
    body.update(kw)
    return db_client.post(f"{V1}/videos", json=body, headers=uploader["headers"])


class TestRegister:
    def test_영상_판정_작업이_함께_저장된다(self, db_client, db_session, uploader):
        key = _upload(db_client, uploader)
        res = _register(db_client, uploader, key)
        assert res.status_code == 201, res.text
        video_id = uuid.UUID(res.json()["id"])

        row = db_session.execute(
            text(
                "SELECT v.storage_key, val.passed, val.reject_reason, j.status"
                " FROM video v"
                " JOIN video_validation val ON val.video_id = v.id"
                " JOIN analysis_job j ON j.video_id = v.id"
                " WHERE v.id = :id"
            ),
            {"id": video_id},
        ).one()
        assert row.storage_key == key
        assert row.passed is True
        assert row.reject_reason is None
        assert row.status == "queued"

    def test_반려는_판정만_남고_작업은_안_생긴다(
        self, db_client, db_session, uploader
    ):
        key = _upload(db_client, uploader)
        res = _register(db_client, uploader, key, width=3840, height=2160)
        assert res.status_code == 201, res.text
        video_id = uuid.UUID(res.json()["id"])

        passed, reason = db_session.execute(
            text(
                "SELECT passed, reject_reason FROM video_validation WHERE video_id = :id"
            ),
            {"id": video_id},
        ).one()
        assert passed is False
        assert "3840x2160" in reason

        jobs = db_session.execute(
            text("SELECT count(*) FROM analysis_job WHERE video_id = :id"),
            {"id": video_id},
        ).scalar_one()
        assert jobs == 0

    def test_없는_종목은_거부된다(self, db_client, uploader):
        """`sport` 를 원시 쿼리로 읽는 자리. 컬럼 이름이 바뀌면 여기서 깨진다."""
        key = _upload(db_client, uploader)
        res = _register(db_client, uploader, key, sport_code="curling")
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "UNKNOWN_SPORT"

    def test_있는_종목은_통과한다(self, db_client, uploader):
        """위 검사의 양성 대조. 둘이 같이 있어야 "종목을 실제로 읽는다"가 된다."""
        key = _upload(db_client, uploader)
        assert _register(db_client, uploader, key, sport_code="baseball").status_code == 201


class TestConstraints:
    def test_영상당_판정은_하나뿐이다(self, db_client, db_session, uploader):
        """부록 D.7 의 유일 제약. **막히지 않으면 그 제약은 없는 것이다.**"""
        key = _upload(db_client, uploader)
        video_id = uuid.UUID(_register(db_client, uploader, key).json()["id"])

        db_session.add(
            VideoValidationOrm(
                id=uuid.uuid4(),
                video_id=video_id,
                passed=False,
                reject_reason="두 번째 판정",
                checked_at=datetime.now(timezone.utc),
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_영상을_지우면_판정도_지워진다(self, db_client, db_session, uploader):
        """SEC-006 의 연쇄. 여기서 끊기면 사용자 삭제가 외래키에서 막힌다."""
        key = _upload(db_client, uploader)
        video_id = uuid.UUID(_register(db_client, uploader, key).json()["id"])

        db_session.execute(text("DELETE FROM video WHERE id = :id"), {"id": video_id})
        db_session.commit()

        left = db_session.execute(
            text("SELECT count(*) FROM video_validation WHERE video_id = :id"),
            {"id": video_id},
        ).scalar_one()
        assert left == 0


class TestListMyVideos:
    def test_최근_것이_앞에_온다(self, db_client, uploader):
        first = _upload(db_client, uploader)
        assert _register(db_client, uploader, first).status_code == 201
        second = _upload(db_client, uploader)
        assert _register(db_client, uploader, second).status_code == 201

        rows = db_client.get(f"{V1}/videos", headers=uploader["headers"]).json()
        assert [r["storage_key"] for r in rows][:2] == [second, first]

    def test_분석_상태와_반려_사유가_같이_온다(self, db_client, uploader):
        ok = _upload(db_client, uploader)
        _register(db_client, uploader, ok)
        rejected = _upload(db_client, uploader)
        _register(db_client, uploader, rejected, duration_ms=90_000)

        rows = {
            r["storage_key"]: r
            for r in db_client.get(
                f"{V1}/videos", headers=uploader["headers"]
            ).json()
        }
        assert rows[ok]["analysis_status"] == "queued"
        assert rows[ok]["reject_reason"] is None
        assert rows[rejected]["analysis_status"] is None
        assert "길이" in rows[rejected]["reject_reason"]
