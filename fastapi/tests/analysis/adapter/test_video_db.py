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
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.analysis.adapter.outbound.orm.analysis_job_orm import AnalysisJobOrm
from app.analysis.adapter.outbound.orm.video_orm import VideoOrm
from app.analysis.adapter.outbound.orm.video_validation_orm import VideoValidationOrm
from app.analysis.adapter.outbound.pg.video_pg_repository import VideoPgRepository
from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _OBJECTS,
    FakeStorage,
    put_object,
    reset_videos,
)
from app.analysis.dependencies.video_providers import get_storage
from app.core.config import settings
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


def _upload(db_client, uploader, size_bytes=SIZE_OK, filename="clip.mp4"):
    res = db_client.post(
        f"{V1}/videos/upload-url",
        json={
            "content_type": "video/mp4",
            "size_bytes": SIZE_OK,
            "filename": filename,
        },
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

    def test_지정_박스가_작업_행에_저장된다(self, db_client, db_session, uploader):
        """미결 `paik` 6번 — 「이 사람으로 분석」 이 `analysis_job` (JSON 컬럼)에 남는다."""
        key = _upload(db_client, uploader)
        res = _register(
            db_client, uploader, key,
            subject_box=[0.39, 0.35, 0.12, 0.4], subject_at_ms=4_200,
        )
        assert res.status_code == 201, res.text
        video_id = uuid.UUID(res.json()["id"])

        box, at = db_session.execute(
            text(
                "SELECT subject_box, subject_at_ms FROM analysis_job"
                " WHERE video_id = :id"
            ),
            {"id": video_id},
        ).one()
        assert box == [0.39, 0.35, 0.12, 0.4]
        assert at == 4_200

    def test_집중_항목이_작업_행에_저장된다(self, db_client, db_session, uploader):
        """미결 `paik` 8번 — `analysis_job.focus`(JSON 컬럼) 에 남는다."""
        key = _upload(db_client, uploader)
        res = _register(
            db_client, uploader, key, focus=["follow_through", "trunk_alignment"]
        )
        assert res.status_code == 201, res.text
        video_id = uuid.UUID(res.json()["id"])

        stored = db_session.execute(
            text("SELECT focus FROM analysis_job WHERE video_id = :id"),
            {"id": video_id},
        ).scalar_one()
        assert stored == ["follow_through", "trunk_alignment"]

    def test_analyze_false_면_지정_박스는_버려진다(
        self, db_client, db_session, uploader
    ):
        """작업 행이 없으니 담을 데가 없다 — 실패로 만들지는 않는다(201)."""
        key = _upload(db_client, uploader)
        res = _register(
            db_client, uploader, key, analyze=False,
            subject_box=[0.1, 0.1, 0.2, 0.2], subject_at_ms=100,
        )
        assert res.status_code == 201, res.text
        left = db_session.execute(
            text(
                "SELECT count(*) FROM analysis_job WHERE video_id = :id"
            ),
            {"id": uuid.UUID(res.json()["id"])},
        ).scalar_one()
        assert left == 0

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

    def test_analyze_false_면_작업_행이_안_생긴다(
        self, db_client, db_session, uploader
    ):
        """미결 `paik` 4번 — 규격 통과해도 `analysis_job` 을 만들지 않는다."""
        key = _upload(db_client, uploader)
        res = _register(db_client, uploader, key, analyze=False)
        assert res.status_code == 201, res.text
        video_id = uuid.UUID(res.json()["id"])

        passed = db_session.execute(
            text("SELECT passed FROM video_validation WHERE video_id = :id"),
            {"id": video_id},
        ).scalar_one()
        assert passed is True

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


class TestVisibility:
    """미결 `paik` 5번(1+2 조각) — 실제 PostgreSQL 에서 공개 여부가 도는지."""

    def test_기본은_비공개로_저장된다(self, db_client, db_session, uploader):
        key = _upload(db_client, uploader)
        video_id = uuid.UUID(_register(db_client, uploader, key).json()["id"])

        is_public = db_session.execute(
            text("SELECT is_public FROM video WHERE id = :id"), {"id": video_id}
        ).scalar_one()
        assert is_public is False

    def test_공개로_바꾸면_남의_공개_목록에_뜬다(self, db_client, uploader):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]

        res = db_client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=uploader["headers"],
        )
        assert res.status_code == 200, res.text
        assert res.json()["is_public"] is True

        # 다른 사람으로 로그인해도 보인다
        other = f"viewer-{uuid.uuid4().hex[:12]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": other, "password": PASSWORD, "nickname": "구경꾼"},
        )
        login = db_client.post(
            f"{V1}/auth/login", json={"email": other, "password": PASSWORD}
        )
        viewer_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
        rows = db_client.get(f"{V1}/videos/public", headers=viewer_h).json()
        assert video_id in [r["id"] for r in rows]

    def test_남의_클립은_못_바꾼다(self, db_client, uploader):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]

        other = f"intruder-{uuid.uuid4().hex[:12]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": other, "password": PASSWORD, "nickname": "침입자"},
        )
        login = db_client.post(
            f"{V1}/auth/login", json={"email": other, "password": PASSWORD}
        )
        h = {"Authorization": f"Bearer {login.json()['access_token']}"}

        res = db_client.patch(
            f"{V1}/videos/{video_id}", json={"is_public": True}, headers=h
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "VIDEO_NOT_FOUND"

    def test_제목_설명을_저장하고_부분_수정한다(self, db_client, db_session, uploader):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]

        db_client.patch(
            f"{V1}/videos/{video_id}",
            json={"title": "첫 골", "description": "왼발"},
            headers=uploader["headers"],
        )
        title, desc = db_session.execute(
            text("SELECT title, description FROM video WHERE id = :id"),
            {"id": uuid.UUID(video_id)},
        ).one()
        assert (title, desc) == ("첫 골", "왼발")

        # description 만 바꾼다 — title 은 그대로
        db_client.patch(
            f"{V1}/videos/{video_id}",
            json={"description": "오른발"},
            headers=uploader["headers"],
        )
        title, desc = db_session.execute(
            text("SELECT title, description FROM video WHERE id = :id"),
            {"id": uuid.UUID(video_id)},
        ).one()
        assert (title, desc) == ("첫 골", "오른발")


class TestPlayback:
    """`GET /videos/{id}/playback-url` — 사전 서명(가짜)까지가 실제 DB 경유."""

    def test_공개_클립은_재생_URL_을_준다(self, db_client, uploader):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]
        db_client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=uploader["headers"],
        )

        res = db_client.get(
            f"{V1}/videos/{video_id}/playback-url", headers=uploader["headers"]
        )
        assert res.status_code == 200, res.text
        assert res.json()["url"].startswith("https://")

    def test_비공개_남의_클립은_404_다(self, db_client, uploader):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]

        other = f"peek-{uuid.uuid4().hex[:12]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": other, "password": PASSWORD, "nickname": "엿보기"},
        )
        login = db_client.post(
            f"{V1}/auth/login", json={"email": other, "password": PASSWORD}
        )
        h = {"Authorization": f"Bearer {login.json()['access_token']}"}

        res = db_client.get(f"{V1}/videos/{video_id}/playback-url", headers=h)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "VIDEO_NOT_FOUND"


class TestDelete:
    def test_지우면_판정도_작업도_함께_사라진다(
        self, db_client, db_session, uploader
    ):
        """미결 jin 24번 — `DELETE /videos/{id}` 가 SEC-006 연쇄를 탄다."""
        key = _upload(db_client, uploader)
        video_id = uuid.UUID(_register(db_client, uploader, key).json()["id"])
        assert (
            db_session.execute(
                text("SELECT count(*) FROM analysis_job WHERE video_id = :id"),
                {"id": video_id},
            ).scalar_one()
            == 1
        )

        res = db_client.delete(
            f"{V1}/videos/{video_id}", headers=uploader["headers"]
        )
        assert res.status_code == 204, res.text

        for tbl in ("video", "video_validation", "analysis_job"):
            left = db_session.execute(
                text(f"SELECT count(*) FROM {tbl} WHERE "
                     f"{'id' if tbl == 'video' else 'video_id'} = :id"),
                {"id": video_id},
            ).scalar_one()
            assert left == 0, tbl

    def test_남의_클립은_404_다(self, db_client, uploader):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]

        other = f"del-{uuid.uuid4().hex[:12]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": other, "password": PASSWORD, "nickname": "남"},
        )
        login = db_client.post(
            f"{V1}/auth/login", json={"email": other, "password": PASSWORD}
        )
        h = {"Authorization": f"Bearer {login.json()['access_token']}"}

        res = db_client.delete(f"{V1}/videos/{video_id}", headers=h)
        assert res.status_code == 404


class TestKeep:
    """미결 jin 24번 2조각 — `POST /videos/{id}/keep` 가 실제 DB 에서 도는지."""

    def test_저장하면_storage_key_가_리포트_자리로_바뀐다(
        self, db_client, db_session, uploader
    ):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]
        assert key.startswith("videos/")

        res = db_client.post(
            f"{V1}/videos/{video_id}/keep", headers=uploader["headers"]
        )
        assert res.status_code == 200, res.text

        stored_key, kept = db_session.execute(
            text("SELECT storage_key, kept FROM video WHERE id = :id"),
            {"id": uuid.UUID(video_id)},
        ).one()
        assert stored_key == f"reports/{uploader['id']}/{video_id}/source.mp4"
        assert kept is True

        # S3(가짜) 객체도 옮겨졌다
        assert key not in _OBJECTS
        assert stored_key in _OBJECTS

        # 재생 주소는 새 키로 나온다
        db_client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=uploader["headers"],
        )
        url = db_client.get(
            f"{V1}/videos/{video_id}/playback-url", headers=uploader["headers"]
        ).json()["url"]
        assert f"source.mp4" in url


class TestReadableKey:
    """미결 jin 24번 — 저장 키에 닉네임·원본이름, `original_filename` 컬럼."""

    def test_키에_실제_닉네임이_들어가고_원본이름이_저장된다(
        self, db_client, db_session, uploader
    ):
        res = db_client.post(
            f"{V1}/videos/upload-url",
            json={
                "content_type": "video/mp4",
                "size_bytes": SIZE_OK,
                "filename": "My Kick.mp4",
            },
            headers=uploader["headers"],
        )
        key = res.json()["storage_key"]
        # `uploader` 픽스처가 닉네임 "업로더" 로 가입한다
        assert key.startswith(f"videos/{uploader['id']}/업로더-My-Kick-")

        put_object(key, SIZE_OK)
        video_id = uuid.UUID(
            _register(db_client, uploader, key, filename="My Kick.mp4").json()["id"]
        )
        stored = db_session.execute(
            text("SELECT original_filename FROM video WHERE id = :id"),
            {"id": video_id},
        ).scalar_one()
        assert stored == "My Kick.mp4"


class TestProvisionalSweep:
    """미결 jin 24번 백스톱 — `VideoPgRepository.sweep_provisional`."""

    def _make(self, db_session, uploader, *, kept, age_hours, job_status=None):
        vid = uuid.uuid4()
        created = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        db_session.add(
            VideoOrm(
                id=vid,
                user_id=uploader["id"],
                sport_code="football",
                storage_key=f"videos/{uploader['id']}/{vid}.mp4",
                duration_ms=5_000,
                side=None,
                kept=kept,
                created_at=created,
            )
        )
        db_session.flush()
        if job_status is not None:
            db_session.add(
                AnalysisJobOrm(
                    id=uuid.uuid4(),
                    video_id=vid,
                    status=job_status,
                    created_at=created,
                )
            )
        db_session.commit()
        return vid

    def test_오래된_미저장분만_지운다(self, db_session, uploader):
        stale = self._make(db_session, uploader, kept=False, age_hours=48)
        recent = self._make(db_session, uploader, kept=False, age_hours=1)
        saved_old = self._make(db_session, uploader, kept=True, age_hours=48)

        swept = VideoPgRepository(db_session).sweep_provisional(ttl_hours=24)
        swept_ids = {v.id for v in swept}

        assert stale in swept_ids
        assert recent not in swept_ids
        assert saved_old not in swept_ids

        left = {
            r[0]
            for r in db_session.execute(
                text("SELECT id FROM video WHERE id = ANY(:ids)"),
                {"ids": [stale, recent, saved_old]},
            )
        }
        assert stale not in left
        assert {recent, saved_old} <= left

    def test_아직_도는_작업이_붙은_것은_안_지운다(self, db_session, uploader):
        """GPU 가 꺼져 있으면 `queued` 로 몇 시간 대기가 정상이다."""
        queued = self._make(
            db_session, uploader, kept=False, age_hours=48, job_status="queued"
        )
        done = self._make(
            db_session, uploader, kept=False, age_hours=48, job_status="failed"
        )

        swept_ids = {
            v.id
            for v in VideoPgRepository(db_session).sweep_provisional(ttl_hours=24)
        }
        assert queued not in swept_ids
        assert done in swept_ids


class TestFeatured:
    """「대표 영상」이 실제 컬럼·부분 유일 인덱스·조인으로 도는지 (미결 `paik` 10번)."""

    def _clip(self, db_client, uploader):
        key = _upload(db_client, uploader)
        res = _register(db_client, uploader, key)
        assert res.status_code == 201, res.text
        return res.json()["id"]

    def test_사람당_하나_부분_유일_인덱스가_지킨다(
        self, db_client, db_session, uploader
    ):
        first = self._clip(db_client, uploader)
        second = self._clip(db_client, uploader)

        for vid in (first, second):
            r = db_client.patch(
                f"{V1}/videos/{vid}",
                json={"is_featured": True},
                headers=uploader["headers"],
            )
            assert r.status_code == 200, r.text

        rows = db_session.execute(
            text(
                "SELECT id::text, is_featured FROM video WHERE user_id = :u"
            ),
            {"u": uploader["id"]},
        ).all()
        featured = [r.id for r in rows if r.is_featured]
        assert featured == [second]   # 하나뿐, 그리고 마지막 것

    def test_남의_대표를_카드_슬러그로_읽는다(self, db_client, db_session, uploader):
        vid = self._clip(db_client, uploader)
        assert db_client.patch(
            f"{V1}/videos/{vid}",
            json={"is_featured": True},
            headers=uploader["headers"],
        ).status_code == 200

        card = db_client.post(f"{V1}/me/card", headers=uploader["headers"])
        assert card.status_code in (200, 201), card.text
        slug = card.json()["public_slug"]

        # 다른 사람으로 로그인해서 읽는다.
        other_email = f"viewer-{uuid.uuid4().hex[:12]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": other_email, "password": PASSWORD, "nickname": "보는이"},
        )
        tok = db_client.post(
            f"{V1}/auth/login", json={"email": other_email, "password": PASSWORD}
        ).json()["access_token"]

        res = db_client.get(
            f"{V1}/cards/{slug}/featured-video",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["video_id"] == vid
        assert body["url"].startswith("https://")

    def test_대표가_없으면_404_다(self, db_client, uploader):
        self._clip(db_client, uploader)   # 대표로 안 세움
        card = db_client.post(f"{V1}/me/card", headers=uploader["headers"])
        slug = card.json()["public_slug"]

        res = db_client.get(
            f"{V1}/cards/{slug}/featured-video", headers=uploader["headers"]
        )
        assert res.status_code == 404


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

    def test_kept_false_인_것은_목록에서_빠진다(self, db_client, db_session, uploader):
        """미결 jin 24번 — 임시(미저장) 영상은 `GET /videos` 에 안 나온다."""
        kept_key = _upload(db_client, uploader)
        _register(db_client, uploader, kept_key)
        prov_key = _upload(db_client, uploader)
        prov_id = uuid.UUID(_register(db_client, uploader, prov_key).json()["id"])

        db_session.execute(
            text("UPDATE video SET kept = false WHERE id = :id"), {"id": prov_id}
        )
        db_session.commit()

        keys = [
            r["storage_key"]
            for r in db_client.get(
                f"{V1}/videos", headers=uploader["headers"]
            ).json()
        ]
        assert kept_key in keys
        assert prov_key not in keys

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


def _email_of(db_client, uploader):
    """`uploader` 픽스처가 만든 이메일을 되찾는다 — 픽스처가 값을 안 돌려줘서."""
    return db_client.get(f"{V1}/me", headers=uploader["headers"]).json()["email"]


class TestAdminVideos:
    """미결 jin 24번 6조각 — `GET/DELETE /admin/videos`.

    `?user=<uid|email>` 를 사람으로 되짚는 것과 소유 검사 없는 삭제 연쇄를
    **진짜 PostgreSQL** 에서 본다(스텁은 `user` 를 모른다).
    """

    @pytest.fixture
    def admin(self, db_client):
        email = f"admin-{uuid.uuid4().hex[:12]}@super-sub.example"
        db_client.post(
            f"{V1}/auth/signup",
            json={"email": email, "password": PASSWORD, "nickname": "관리자"},
        )
        original = settings.admin_emails
        settings.admin_emails = email
        login = db_client.post(
            f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
        )
        try:
            yield {
                "email": email,
                "headers": {
                    "Authorization": f"Bearer {login.json()['access_token']}"
                },
            }
        finally:
            settings.admin_emails = original

    def test_이메일로도_UUID로도_그_사람의_영상을_찾는다(
        self, db_client, uploader, admin
    ):
        key = _upload(db_client, uploader)
        video_id = _register(db_client, uploader, key).json()["id"]

        # 대소문자를 섞어 보내 이메일 조회가 대소문자를 무시하는지 함께 본다
        email = _email_of(db_client, uploader)
        by_email = db_client.get(
            f"{V1}/admin/videos", params={"user": email.upper()}, headers=admin["headers"]
        )
        assert by_email.status_code == 200, by_email.text
        assert [r["id"] for r in by_email.json()["items"]] == [video_id]
        assert by_email.json()["email"] == email
        assert by_email.json()["nickname"] == "업로더"

        by_uuid = db_client.get(
            f"{V1}/admin/videos",
            params={"user": str(uploader["id"])},
            headers=admin["headers"],
        )
        assert [r["id"] for r in by_uuid.json()["items"]] == [video_id]

    def test_닉네임을_바꾸면_현재_값으로_보인다(self, db_client, uploader, admin):
        key = _upload(db_client, uploader)
        _register(db_client, uploader, key)

        db_client.patch(
            f"{V1}/me", json={"nickname": "새이름"}, headers=uploader["headers"]
        )
        body = db_client.get(
            f"{V1}/admin/videos",
            params={"user": str(uploader["id"])},
            headers=admin["headers"],
        ).json()
        # 옛 저장 키에는 "업로더" 가 얼어붙어 있지만 목록은 DB 조인이라 현재 값이다
        assert body["nickname"] == "새이름"
        assert "업로더-" in body["items"][0]["storage_key"]

    def test_아직_저장_안_한_임시분도_관리자에게는_보인다(
        self, db_client, db_session, uploader, admin
    ):
        prov_key = _upload(db_client, uploader)
        prov_id = uuid.UUID(_register(db_client, uploader, prov_key).json()["id"])
        db_session.execute(
            text("UPDATE video SET kept = false WHERE id = :id"), {"id": prov_id}
        )
        db_session.commit()

        # 본인 목록엔 안 나온다
        assert prov_key not in [
            r["storage_key"]
            for r in db_client.get(
                f"{V1}/videos", headers=uploader["headers"]
            ).json()
        ]
        # 관리자 목록엔 나온다
        rows = db_client.get(
            f"{V1}/admin/videos",
            params={"user": str(uploader["id"])},
            headers=admin["headers"],
        ).json()["items"]
        row = next(r for r in rows if r["id"] == str(prov_id))
        assert row["kept"] is False

    def test_실패_사유가_관리자_목록에는_보이고_상태만_있던_자리를_채운다(
        self, db_client, db_session, uploader, admin
    ):
        key = _upload(db_client, uploader)
        video_id = uuid.UUID(_register(db_client, uploader, key).json()["id"])
        reason = "품질 게이트 미달: 유효 프레임 비율 53% < 기준 70%."
        db_session.execute(
            text(
                "UPDATE analysis_job SET status = 'failed', failure_reason = :r "
                "WHERE video_id = :id"
            ),
            {"r": reason, "id": video_id},
        )
        db_session.commit()

        rows = db_client.get(
            f"{V1}/admin/videos",
            params={"user": str(uploader["id"])},
            headers=admin["headers"],
        ).json()["items"]
        row = next(r for r in rows if r["id"] == str(video_id))
        assert row["analysis_status"] == "failed"
        assert row["analysis_failure_reason"] == reason

    def test_없는_사람이면_404(self, db_client, admin):
        res = db_client.get(
            f"{V1}/admin/videos",
            params={"user": "ghost@super-sub.example"},
            headers=admin["headers"],
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "USER_NOT_FOUND"

    def test_관리자는_남의_영상을_지운다_연쇄까지(
        self, db_client, db_session, uploader, admin
    ):
        key = _upload(db_client, uploader)
        video_id = uuid.UUID(_register(db_client, uploader, key).json()["id"])

        res = db_client.delete(
            f"{V1}/admin/videos/{video_id}", headers=admin["headers"]
        )
        assert res.status_code == 204, res.text
        for tbl in ("video", "video_validation", "analysis_job"):
            col = "id" if tbl == "video" else "video_id"
            left = db_session.execute(
                text(f"SELECT count(*) FROM {tbl} WHERE {col} = :id"),
                {"id": video_id},
            ).scalar_one()
            assert left == 0, tbl

    def test_없는_클립_삭제는_404(self, db_client, admin):
        res = db_client.delete(
            f"{V1}/admin/videos/{uuid.uuid4()}", headers=admin["headers"]
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "VIDEO_NOT_FOUND"
