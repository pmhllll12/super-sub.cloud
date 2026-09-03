"""analysis/adapter/inbound/api/v1/video_router.py — 계약 문서 3-5절.

스텁을 끼워 DB·S3 없이 돈다. 실제 저장·연쇄는 `test_video_db.py` 가 본다.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.video_stub_repository import (
    put_object,
    reset_videos,
)
from app.analysis.domain.rules.video_rules import MAX_BYTES, MAX_DURATION_MS
from app.core.security import issue_access_token
from tests.conftest import V1, error_code

SIZE_OK = 50 * 1024 * 1024


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_videos()
    yield
    reset_videos()


def _issue(client, user_id, content_type="video/mp4", size_bytes=SIZE_OK):
    res = client.post(
        f"{V1}/videos/upload-url",
        json={"content_type": content_type, "size_bytes": size_bytes},
        headers=_headers(user_id),
    )
    assert res.status_code == 200, res.text
    return res.json()["storage_key"]


def _register(client, user_id, storage_key, **kw):
    body = {
        "sport_code": "football",
        "storage_key": storage_key,
        "duration_ms": 10_000,
        "width": 1920,
        "height": 1080,
    }
    body.update(kw)
    return client.post(f"{V1}/videos", json=body, headers=_headers(user_id))


class TestUploadUrl:
    def test_인증이_필요하다(self, client):
        res = client.post(
            f"{V1}/videos/upload-url",
            json={"content_type": "video/mp4", "size_bytes": SIZE_OK},
        )
        assert res.status_code == 401

    def test_자리를_받으면_키와_URL_이_온다(self, client):
        user_id = uuid4()
        res = client.post(
            f"{V1}/videos/upload-url",
            json={"content_type": "video/mp4", "size_bytes": SIZE_OK},
            headers=_headers(user_id),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["storage_key"].startswith(f"videos/{user_id}/")
        assert body["storage_key"].endswith(".mp4")
        assert body["upload_url"] and body["expires_in"] > 0

    def test_모르는_형식은_거부한다(self, client):
        res = client.post(
            f"{V1}/videos/upload-url",
            json={"content_type": "video/x-msvideo", "size_bytes": SIZE_OK},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 422
        assert error_code(res) == "UNSUPPORTED_FORMAT"

    def test_상한을_넘는_용량은_URL_을_안_준다(self, client):
        """헛걸음을 줄이는 자리다. 진짜 상한은 등록할 때 실측으로 건다."""
        res = client.post(
            f"{V1}/videos/upload-url",
            json={"content_type": "video/mp4", "size_bytes": MAX_BYTES + 1},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 422
        assert error_code(res) == "FILE_TOO_LARGE"


class TestRegisterVideo:
    def test_인증이_필요하다(self, client):
        res = client.post(f"{V1}/videos", json={})
        assert res.status_code == 401

    def test_규격에_맞으면_통과하고_작업이_생긴다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, side="right")
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["passed"] is True
        assert body["reject_reason"] is None
        assert body["analysis_job_id"] is not None
        assert body["analysis_status"] == "queued"
        assert body["side"] == "right"

    def test_반려도_201_이고_사유가_본문에_온다(self, client):
        """🔴 422 로 돌려보내면 사유가 아무 데도 안 남는다 — SFR-001."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, duration_ms=MAX_DURATION_MS + 1)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["passed"] is False
        assert "길이" in body["reject_reason"]

    def test_반려된_클립은_분석하지_않는다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, width=3840, height=2160)
        body = res.json()
        assert body["passed"] is False
        assert body["analysis_job_id"] is None
        assert body["analysis_status"] is None

    def test_올리지_않은_키는_반려가_아니라_에러다(self, client):
        """검사할 파일이 없다. 반려로 기록하면 "안 올린 것"과 구별되지 않는다."""
        user_id = uuid4()
        key = _issue(client, user_id)

        res = _register(client, user_id, key)
        assert res.status_code == 422
        assert error_code(res) == "FILE_NOT_UPLOADED"

    def test_상한_초과는_올라온_크기로_잡는다(self, client):
        """사전 서명 URL 은 크기를 강제하지 못한다. 그래서 실측이 진짜 검사다."""
        user_id = uuid4()
        key = _issue(client, user_id, size_bytes=SIZE_OK)
        put_object(key, MAX_BYTES + 1)

        res = _register(client, user_id, key)
        assert res.status_code == 201, res.text
        assert res.json()["passed"] is False
        assert "용량" in res.json()["reject_reason"]

    def test_남의_저장_키로는_등록할_수_없다(self, client):
        other = uuid4()
        key = _issue(client, other)
        put_object(key, SIZE_OK)

        res = _register(client, uuid4(), key)
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_없는_종목은_거부한다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, sport_code="curling")
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_SPORT"


class TestListMyVideos:
    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/videos").status_code == 401

    def test_없으면_빈_배열이다(self, client):
        res = client.get(f"{V1}/videos", headers=_headers(uuid4()))
        assert res.status_code == 200
        assert res.json() == []

    def test_내_것만_담긴다(self, client):
        mine, other = uuid4(), uuid4()
        for user_id in (mine, other):
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            assert _register(client, user_id, key).status_code == 201

        res = client.get(f"{V1}/videos", headers=_headers(mine))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_반려_사유가_목록에도_온다(self, client):
        """`/videos` 화면이 반려 사유를 펼쳐 보여준다(플러터 설계 5.3)."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        _register(client, user_id, key, width=3840, height=2160)

        row = client.get(f"{V1}/videos", headers=_headers(user_id)).json()[0]
        assert row["passed"] is False
        assert "해상도" in row["reject_reason"]
