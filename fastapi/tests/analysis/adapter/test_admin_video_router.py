"""analysis/adapter/inbound/api/v1/admin_video_router.py — 계약 문서 3-2절.

미결 `jin` 24번 6조각. 스텁을 끼워 DB·S3 없이 돈다 — `?user=` 를 이메일로
되짚는 실제 조회와 S3 정리는 `test_video_db.py` 가 본다.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _OBJECTS,
    put_object,
    reset_videos,
)
from app.core.config import settings
from app.core.security import issue_access_token
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_USER_ID,
)
from tests.conftest import V1, error_code

SIZE_OK = 50 * 1024 * 1024


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture
def admin_headers():
    """데모 계정을 관리자 화이트리스트에 잠깐 넣는다(`test_admin_router` 와 같은 결).

    conftest 의 `_stub_user_email_reader` 가 `DEMO_USER_ID` 만 이메일로 되짚으므로
    관리자로 행동하는 토큰은 그 사람이어야 한다.
    """
    original = settings.admin_emails
    settings.admin_emails = DEMO_EMAIL
    try:
        yield _headers(DEMO_USER_ID)
    finally:
        settings.admin_emails = original


@pytest.fixture(autouse=True)
def _clean():
    reset_videos()
    yield
    reset_videos()


def _add_clip(client, owner):
    key = client.post(
        f"{V1}/videos/upload-url",
        json={"content_type": "video/mp4", "size_bytes": SIZE_OK, "filename": "clip.mp4"},
        headers=_headers(owner),
    ).json()["storage_key"]
    put_object(key, SIZE_OK)
    res = client.post(
        f"{V1}/videos",
        json={
            "sport_code": "football",
            "storage_key": key,
            "duration_ms": 10_000,
            "width": 1920,
            "height": 1080,
            "filename": "clip.mp4",
        },
        headers=_headers(owner),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"], key


class TestAdminGate:
    def test_헤더가_없으면_401(self, client):
        assert client.get(f"{V1}/admin/videos", params={"user": str(uuid4())}).status_code == 401

    def test_관리자가_아니면_403(self, client):
        res = client.get(
            f"{V1}/admin/videos",
            params={"user": str(uuid4())},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"


class TestListAdminVideos:
    def test_user_파라미터가_없으면_422(self, client, admin_headers):
        res = client.get(f"{V1}/admin/videos", headers=admin_headers)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_그_사람의_영상이_전부_온다(self, client, admin_headers):
        target = uuid4()
        id1, _ = _add_clip(client, target)
        id2, _ = _add_clip(client, target)
        _add_clip(client, uuid4())  # 남의 것

        res = client.get(
            f"{V1}/admin/videos", params={"user": str(target)}, headers=admin_headers
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["user_id"] == str(target)
        assert {row["id"] for row in body["items"]} == {id1, id2}

    def test_한_줄에_사람이_읽는_값과_되짚을_키가_있다(self, client, admin_headers):
        target = uuid4()
        video_id, key = _add_clip(client, target)

        row = client.get(
            f"{V1}/admin/videos", params={"user": str(target)}, headers=admin_headers
        ).json()["items"][0]
        assert row["original_filename"] == "clip.mp4"
        assert row["storage_key"] == key
        assert row["report_prefix"] == f"reports/{target}/{video_id}/"
        # 🔴 작업이 생긴 클립은 등록만으로는 임시(`kept=false`)다(미결 `jin`
        # 24번 5조각 해소, 2026-09-11) — `POST /videos/{id}/keep` 을 불러야
        # 영구가 된다. 관리자 목록은 임시분까지 다 보여줘야 하므로(위
        # `kept_only=False`) 여기 뜨는 것 자체는 그대로다.
        assert row["kept"] is False
        assert row["passed"] is True

    def test_영상이_없어도_사람이_있으면_빈_목록이다(self, client, admin_headers):
        res = client.get(
            f"{V1}/admin/videos", params={"user": str(uuid4())}, headers=admin_headers
        )
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_없는_사람이면_404(self, client, admin_headers):
        res = client.get(
            f"{V1}/admin/videos",
            params={"user": "nobody@example.com"},
            headers=admin_headers,
        )
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"


class TestAdminDeleteVideo:
    def test_아무_영상이나_지울_수_있다(self, client, admin_headers):
        owner = uuid4()
        video_id, key = _add_clip(client, owner)
        report_key = f"reports/{owner}/{video_id}/report.json"
        put_object(report_key, 10)

        res = client.delete(f"{V1}/admin/videos/{video_id}", headers=admin_headers)
        assert res.status_code == 204, res.text
        assert client.get(f"{V1}/videos", headers=_headers(owner)).json() == []
        assert key not in _OBJECTS
        assert report_key not in _OBJECTS

    def test_없는_클립은_404(self, client, admin_headers):
        res = client.delete(f"{V1}/admin/videos/{uuid4()}", headers=admin_headers)
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_관리자가_아니면_403(self, client):
        res = client.delete(
            f"{V1}/admin/videos/{uuid4()}", headers=_headers(uuid4())
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"
