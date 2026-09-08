"""analysis/adapter/inbound/api/v1/video_router.py — 계약 문서 3-5절.

스텁을 끼워 DB·S3 없이 돈다. 실제 저장·연쇄는 `test_video_db.py` 가 본다.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _OBJECTS,
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


def _issue(
    client, user_id, content_type="video/mp4", size_bytes=SIZE_OK, filename="clip.mp4"
):
    res = client.post(
        f"{V1}/videos/upload-url",
        json={
            "content_type": content_type,
            "size_bytes": size_bytes,
            "filename": filename,
        },
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
            json={"content_type": "video/mp4", "size_bytes": SIZE_OK, "filename": "c.mp4"},
        )
        assert res.status_code == 401

    def test_자리를_받으면_키와_URL_이_온다(self, client):
        user_id = uuid4()
        res = client.post(
            f"{V1}/videos/upload-url",
            json={"content_type": "video/mp4", "size_bytes": SIZE_OK, "filename": "c.mp4"},
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
            json={"content_type": "video/x-msvideo", "size_bytes": SIZE_OK, "filename": "c.avi"},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 422
        assert error_code(res) == "UNSUPPORTED_FORMAT"

    def test_상한을_넘는_용량은_URL_을_안_준다(self, client):
        """헛걸음을 줄이는 자리다. 진짜 상한은 등록할 때 실측으로 건다."""
        res = client.post(
            f"{V1}/videos/upload-url",
            json={"content_type": "video/mp4", "size_bytes": MAX_BYTES + 1, "filename": "c.mp4"},
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
        # 미결 jin 24번 1조각 — 지금은 등록되는 모든 영상이 kept=true 로 시작한다.
        assert body["kept"] is True

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

    def test_analyze_false_면_통과해도_작업이_안_생긴다(self, client):
        """기록용 업로드 — 미결 `paik` 4번. 규격은 검사하되 분석은 안 건다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, analyze=False)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["passed"] is True
        assert body["reject_reason"] is None
        assert body["analysis_job_id"] is None
        assert body["analysis_status"] is None

    def test_analyze_기본값은_작업을_만든다(self, client):
        """🔴 값을 안 보내면 지금처럼 분석이 걸려야 한다 — 화면 저장이 그 동작에 기댄다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        # analyze 를 아예 안 실어 보낸다
        res = _register(client, user_id, key)
        assert res.json()["analysis_job_id"] is not None

    def test_analyze_false_라도_용량_길이_반려는_그대로다(self, client):
        """용량·길이는 `analyze` 와 무관하게 검사한다 — 사유는 값으로 남는다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, analyze=False, duration_ms=MAX_DURATION_MS + 1)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["passed"] is False
        assert "길이" in body["reject_reason"]
        assert body["analysis_job_id"] is None

    def test_analyze_false_면_4K_도_통과한다(self, client):
        """해상도 상한은 분석 워커를 지키는 값이라 기록용 업로드엔 안 건다(미결 `ho` 9번)."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, analyze=False, width=3840, height=2160)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["passed"] is True
        assert body["reject_reason"] is None
        assert body["analysis_job_id"] is None

    def test_analyze_true_면_4K_는_그대로_반려된다(self, client):
        """분석을 걸면 해상도 상한이 살아 있다 — 4K 는 host RAM 이 터진다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, width=3840, height=2160)  # analyze 기본 True
        assert res.status_code == 201, res.text
        assert res.json()["passed"] is False
        assert "해상도" in res.json()["reject_reason"]

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


def _register_clip(client, user_id):
    key = _issue(client, user_id)
    put_object(key, SIZE_OK)
    res = _register(client, user_id, key)
    assert res.status_code == 201, res.text
    return res.json()["id"]


class TestUpdateVideo:
    def test_인증이_필요하다(self, client):
        assert client.patch(f"{V1}/videos/{uuid4()}", json={"is_public": True}).status_code == 401

    def test_제목과_설명을_정할_수_있다(self, client):
        user_id = uuid4()
        video_id = _register_clip(client, user_id)

        res = client.patch(
            f"{V1}/videos/{video_id}",
            json={"title": "우리 팀 첫 골", "description": "왼발 감아차기"},
            headers=_headers(user_id),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["title"] == "우리 팀 첫 골"
        assert body["description"] == "왼발 감아차기"

        row = client.get(f"{V1}/videos", headers=_headers(user_id)).json()[0]
        assert row["title"] == "우리 팀 첫 골"

    def test_보낸_필드만_바뀐다(self, client):
        user_id = uuid4()
        video_id = _register_clip(client, user_id)
        client.patch(
            f"{V1}/videos/{video_id}",
            json={"title": "제목"},
            headers=_headers(user_id),
        )

        # is_public 만 바꾼다 — title 은 그대로여야 한다
        res = client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=_headers(user_id),
        )
        assert res.json()["title"] == "제목"
        assert res.json()["is_public"] is True

    def test_공백_제목은_지운_것으로_본다(self, client):
        user_id = uuid4()
        video_id = _register_clip(client, user_id)
        client.patch(
            f"{V1}/videos/{video_id}", json={"title": "제목"}, headers=_headers(user_id)
        )

        res = client.patch(
            f"{V1}/videos/{video_id}", json={"title": "   "}, headers=_headers(user_id)
        )
        assert res.json()["title"] is None

    def test_제목_상한을_넘으면_422_다(self, client):
        user_id = uuid4()
        video_id = _register_clip(client, user_id)
        res = client.patch(
            f"{V1}/videos/{video_id}",
            json={"title": "가" * 101},
            headers=_headers(user_id),
        )
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_기본은_비공개이고_공개로_바꿀_수_있다(self, client):
        user_id = uuid4()
        video_id = _register_clip(client, user_id)

        rows = client.get(f"{V1}/videos", headers=_headers(user_id)).json()
        assert rows[0]["is_public"] is False

        res = client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=_headers(user_id),
        )
        assert res.status_code == 200, res.text
        assert res.json()["is_public"] is True

    def test_남의_클립은_404_다(self, client):
        owner = uuid4()
        video_id = _register_clip(client, owner)

        res = client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_없는_클립도_404_다(self, client):
        res = client.patch(
            f"{V1}/videos/{uuid4()}",
            json={"is_public": True},
            headers=_headers(uuid4()),
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"


class TestListPublicVideos:
    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/videos/public").status_code == 401

    def test_공개한_것만_남의_눈에도_보인다(self, client):
        owner, viewer = uuid4(), uuid4()
        pub = _register_clip(client, owner)
        _register_clip(client, owner)  # 비공개로 남겨 둔다

        assert client.get(f"{V1}/videos/public", headers=_headers(viewer)).json() == []

        client.patch(
            f"{V1}/videos/{pub}", json={"is_public": True}, headers=_headers(owner)
        )
        rows = client.get(f"{V1}/videos/public", headers=_headers(viewer)).json()
        assert [r["id"] for r in rows] == [pub]

    def test_저장_키와_업로더는_안_실린다(self, client):
        owner = uuid4()
        video_id = _register_clip(client, owner)
        client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=_headers(owner),
        )
        row = client.get(f"{V1}/videos/public", headers=_headers(uuid4())).json()[0]
        assert set(row) == {
            "id",
            "sport_code",
            "duration_ms",
            "created_at",
            "title",
            "description",
        }

    def test_제목과_설명이_실린다(self, client):
        owner = uuid4()
        video_id = _register_clip(client, owner)
        client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True, "title": "제목", "description": "설명"},
            headers=_headers(owner),
        )
        row = client.get(f"{V1}/videos/public", headers=_headers(uuid4())).json()[0]
        assert row["title"] == "제목"
        assert row["description"] == "설명"


class TestPlaybackUrl:
    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/videos/{uuid4()}/playback-url").status_code == 401

    def test_공개_클립은_남도_URL_을_받는다(self, client):
        owner, viewer = uuid4(), uuid4()
        video_id = _register_clip(client, owner)
        client.patch(
            f"{V1}/videos/{video_id}", json={"is_public": True}, headers=_headers(owner)
        )

        res = client.get(
            f"{V1}/videos/{video_id}/playback-url", headers=_headers(viewer)
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["url"].startswith("https://")
        assert body["expires_in"] > 0

    def test_자기_비공개_클립은_URL_을_받는다(self, client):
        owner = uuid4()
        video_id = _register_clip(client, owner)  # 비공개

        res = client.get(
            f"{V1}/videos/{video_id}/playback-url", headers=_headers(owner)
        )
        assert res.status_code == 200, res.text

    def test_비공개_남의_클립은_404_다(self, client):
        owner, viewer = uuid4(), uuid4()
        video_id = _register_clip(client, owner)  # 비공개

        res = client.get(
            f"{V1}/videos/{video_id}/playback-url", headers=_headers(viewer)
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_없는_클립은_404_다(self, client):
        res = client.get(
            f"{V1}/videos/{uuid4()}/playback-url", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"


class TestDeleteVideo:
    def test_인증이_필요하다(self, client):
        assert client.delete(f"{V1}/videos/{uuid4()}").status_code == 401

    def test_자기_클립을_지우면_204_이고_목록에서_빠진다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        video_id = _register(client, user_id, key).json()["id"]

        res = client.delete(f"{V1}/videos/{video_id}", headers=_headers(user_id))
        assert res.status_code == 204, res.text
        assert client.get(f"{V1}/videos", headers=_headers(user_id)).json() == []

    def test_S3_객체와_리포트_접두사도_지운다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        video_id = _register(client, user_id, key).json()["id"]
        report_key = f"reports/{user_id}/{video_id}/report.json"
        put_object(report_key, 10)

        client.delete(f"{V1}/videos/{video_id}", headers=_headers(user_id))
        assert key not in _OBJECTS
        assert report_key not in _OBJECTS

    def test_남의_클립은_404_다(self, client):
        owner = uuid4()
        key = _issue(client, owner)
        put_object(key, SIZE_OK)
        video_id = _register(client, owner, key).json()["id"]

        res = client.delete(f"{V1}/videos/{video_id}", headers=_headers(uuid4()))
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_없는_클립은_404_다(self, client):
        res = client.delete(
            f"{V1}/videos/{uuid4()}", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"


class TestKeepVideo:
    """미결 jin 24번 2조각 — `POST /videos/{id}/keep`."""

    def test_인증이_필요하다(self, client):
        assert client.post(f"{V1}/videos/{uuid4()}/keep").status_code == 401

    def test_저장하면_원본이_리포트_자리로_옮겨진다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        video_id = _register(client, user_id, key).json()["id"]

        res = client.post(f"{V1}/videos/{video_id}/keep", headers=_headers(user_id))
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["kept"] is True
        assert body["storage_key"] == f"reports/{user_id}/{video_id}/source.mp4"

        # S3 객체도 새 자리로 옮겨졌다 (옛 키는 사라진다)
        assert key not in _OBJECTS
        assert f"reports/{user_id}/{video_id}/source.mp4" in _OBJECTS

    def test_두_번_불러도_200_이고_두_번째는_그대로다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        video_id = _register(client, user_id, key).json()["id"]

        first = client.post(
            f"{V1}/videos/{video_id}/keep", headers=_headers(user_id)
        ).json()["storage_key"]
        second = client.post(
            f"{V1}/videos/{video_id}/keep", headers=_headers(user_id)
        )
        assert second.status_code == 200
        assert second.json()["storage_key"] == first

    def test_분석_작업이_없는_클립은_옮기지_않는다(self, client):
        """`/me` 업로드(`analyze:false`)는 리포트 폴더가 없어 `videos/` 에 둔다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        video_id = _register(client, user_id, key, analyze=False).json()["id"]

        res = client.post(f"{V1}/videos/{video_id}/keep", headers=_headers(user_id))
        assert res.status_code == 200, res.text
        assert res.json()["storage_key"] == key
        assert res.json()["kept"] is True

    def test_남의_클립은_404_다(self, client):
        owner = uuid4()
        key = _issue(client, owner)
        put_object(key, SIZE_OK)
        video_id = _register(client, owner, key).json()["id"]

        res = client.post(
            f"{V1}/videos/{video_id}/keep", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"

    def test_없는_클립은_404_다(self, client):
        res = client.post(
            f"{V1}/videos/{uuid4()}/keep", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "VIDEO_NOT_FOUND"
