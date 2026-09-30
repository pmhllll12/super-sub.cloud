"""analysis/adapter/inbound/api/v1/video_router.py — 계약 문서 3-5절.

스텁을 끼워 DB·S3 없이 돈다. 실제 저장·연쇄는 `test_video_db.py` 가 본다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.analysis.adapter.outbound.stub.video_stub_repository import (
    _OBJECTS,
    StubVideoRepository,
    put_object,
    register_card_slug,
    register_nickname,
    register_card_notes,
    register_report_grade,
    register_trust_counts,
    reset_videos,
)
from app.analysis.domain.entities.video_entity import VideoEntity
from app.analysis.domain.rules.video_rules import (
    MAX_BYTES,
    MAX_DURATION_MS,
    MAX_VIDEOS_PER_GROUP,
)
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
        # 미결 jin 24번 5조각 해소(2026-09-11) — 작업이 생긴 클립은 등록만으로는
        # 임시(`kept=false`)다. `POST /videos/{id}/keep` 을 불러야 영구가 된다
        # (`TestKeepVideo` 참고) — 안 그러면 분석에 실패해 다시 볼 리포트가
        # 없는 클립이 DB·S3 에 영영 남는다(사용자가 화면에서 직접 지적).
        assert body["kept"] is False

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
        # 🔴 해상도는 2026-09-19 결정으로 더는 반려 사유가 아니다 — 길이 초과로 반려시킨다.
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, duration_ms=MAX_DURATION_MS + 1)
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

    def test_analyze_true_여도_해상도는_상한이_없다(self, client):
        """결정(2026-09-19, 박민호 — `jin` 43번) — 해상도 상한 자체를 없앴다.
        4K·8K·DCI 4K 세로 전부 통과해야 한다."""
        user_id = uuid4()
        for width, height in [(3840, 2160), (2160, 3840), (7680, 4320), (2160, 4096)]:
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            res = _register(client, user_id, key, width=width, height=height)
            assert res.status_code == 201, res.text
            assert res.json()["passed"] is True
            assert res.json()["reject_reason"] is None
            assert res.json()["analysis_job_id"] is not None

    def test_지정_박스를_받는다(self, client):
        """미결 `paik` 6번 — 「이 사람으로 분석」 박스. 응답엔 안 실린다(작업 값)."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(
            client, user_id, key,
            subject_box=[0.39, 0.35, 0.12, 0.4], subject_at_ms=4_200,
        )
        assert res.status_code == 201, res.text
        assert res.json()["passed"] is True

    def test_픽셀_좌표는_422_다(self, client):
        """🔴 정규화 좌표만. 조용히 클램프하면 엉뚱한 사람을 분석하고도 지정대로라 답한다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(
            client, user_id, key, subject_box=[340, 210, 120, 400], subject_at_ms=4_200
        )
        assert res.status_code == 422

    def test_박스만_주고_시각을_안_주면_422_다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, subject_box=[0.1, 0.1, 0.2, 0.2])
        assert res.status_code == 422

    def test_화면을_벗어나는_박스는_422_다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(
            client, user_id, key, subject_box=[0.8, 0.1, 0.5, 0.2], subject_at_ms=100
        )
        assert res.status_code == 422

    def test_시각이_클립_길이를_넘으면_422_다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(
            client, user_id, key,
            subject_box=[0.1, 0.1, 0.2, 0.2], subject_at_ms=10_001,  # duration 10_000
        )
        assert res.status_code == 422

    def test_집중_항목을_받는다(self, client):
        """미결 `paik` 8번 — 「어디를 집중해서 볼지」 루브릭 criteria id 목록."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(
            client, user_id, key, focus=["follow_through", "guide_hand"]
        )
        assert res.status_code == 201, res.text
        assert res.json()["passed"] is True

    def test_빈_집중_목록은_전체다_실패가_아니다(self, client):
        """🔴 「전체적으로」가 기본이자 가장 흔한 경우 — 실패로 만들지 않는다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, focus=[])
        assert res.status_code == 201, res.text

    def test_집중_목록의_공백·중복은_정리된다(self, client):
        """자유 문자열은 아니지만 형식은 서버가 정리한다(공백·중복 제거)."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(
            client, user_id, key,
            focus=["  follow_through ", "follow_through", " "],
        )
        assert res.status_code == 201, res.text

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

    def test_내려간_종목은_없는_종목과_다른_code_다(self, client):
        """`ho` 39번 — 행은 있지만 루브릭이 없어 지금 안 받는 종목이다.

        🔴 `UNKNOWN_SPORT`(없다)와 가른다. 화면이 「오타」와 「지금은 축구만」을
        다르게 안내할 수 있어야 하고, 되살릴 때 행을 다시 넣을 필요도 없다.
        """
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)

        res = _register(client, user_id, key, sport_code="baseball")
        assert res.status_code == 422
        assert error_code(res) == "SPORT_NOT_AVAILABLE"


class TestDuplicateDetection:
    """`ho` 41번 — 같은 내용을 다시 올리면 새 작업 없이 앞선 결과를 알려준다."""

    HASH = "deadbeef" * 4  # 32자, MD5 hex 자리수

    def _seed_prior(self, user_id, *, status, failure_reason=None, **kw):
        """분석까지 끝난 영상이 이미 있다고 스텁에 직접 심는다.

        실제로는 등록→워커가 집음→완료 보고로 이 상태가 만들어지지만, 완료
        보고 경로(`job_router`)는 별도 스텁 저장소(`job_stub_repository`)를
        쓰고 `_VIDEOS`(영상 스텁)를 갱신하지 않는다 — 계약 테스트 층에서는
        이 상태를 직접 구성하는 것이 맞다. 진짜 DB로 끝까지 잇는 흐름은
        `test_video_db.py` 가 본다.
        """
        prior_id = uuid4()
        StubVideoRepository().register(
            VideoEntity(
                id=prior_id,
                user_id=user_id,
                sport_code="football",
                storage_key=f"videos/{user_id}/prior.mp4",
                duration_ms=10_000,
                side=None,
                created_at=datetime.now(timezone.utc),
                analysis_job_id=uuid4(),
                analysis_status=status,
                analysis_failure_reason=failure_reason,
                content_hash=self.HASH,
                **kw,
            )
        )
        return prior_id

    def test_같은_내용이_실패했었으면_새_작업_없이_그_사유를_알려준다(self, client):
        user_id = uuid4()
        prior_id = self._seed_prior(
            user_id,
            status="failed",
            failure_reason="품질 게이트 미달: 하반신 스윙 측 키포인트 유효 프레임 비율 53% < 기준 70%.",
        )

        key = _issue(client, user_id)
        put_object(key, SIZE_OK, content_hash=self.HASH)

        res = _register(client, user_id, key)
        assert res.status_code == 201, res.text
        body = res.json()
        # 새 작업은 안 만든다 — GPU를 또 태우지 않는다.
        assert body["analysis_job_id"] is None
        assert body["analysis_status"] is None
        assert body["duplicate_of_video_id"] == str(prior_id)
        assert body["duplicate_status"] == "failed"
        assert "53%" in body["duplicate_failure_reason"]

    def test_같은_내용이_성공했었으면_새_작업_없이_그_사실을_알려준다(self, client):
        user_id = uuid4()
        prior_id = self._seed_prior(user_id, status="succeeded")

        key = _issue(client, user_id)
        put_object(key, SIZE_OK, content_hash=self.HASH)

        res = _register(client, user_id, key)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["analysis_job_id"] is None
        assert body["duplicate_of_video_id"] == str(prior_id)
        assert body["duplicate_status"] == "succeeded"
        assert body["duplicate_failure_reason"] is None

    def test_내용_지문을_모르면_중복_판단을_안_한다(self, client):
        """S3 가 ETag 를 못 주면(멀티파트 등) 중복 여부를 모른다로 처리한다."""
        user_id = uuid4()
        self._seed_prior(user_id, status="failed", failure_reason="사유")

        key = _issue(client, user_id)
        put_object(key, SIZE_OK)  # content_hash 안 줌

        res = _register(client, user_id, key)
        body = res.json()
        assert body["analysis_job_id"] is not None
        assert body["duplicate_of_video_id"] is None

    def test_다른_사람이_올린_같은_내용은_중복이_아니다(self, client):
        """`user_id`로 좁힌다 — 남의 과거 결과를 빌려오지 않는다."""
        other_user = uuid4()
        self._seed_prior(other_user, status="failed", failure_reason="사유")

        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK, content_hash=self.HASH)

        res = _register(client, user_id, key)
        body = res.json()
        assert body["analysis_job_id"] is not None
        assert body["duplicate_of_video_id"] is None

    def test_박스_지정이_있으면_중복_판단을_안_한다(self, client):
        """같은 영상이어도 누구를 보라고 골랐는지가 다르면 결과가 다를 수 있다."""
        user_id = uuid4()
        self._seed_prior(user_id, status="succeeded")

        key = _issue(client, user_id)
        put_object(key, SIZE_OK, content_hash=self.HASH)

        res = _register(
            client, user_id, key,
            subject_box=[0.1, 0.1, 0.2, 0.2], subject_at_ms=100,
        )
        body = res.json()
        assert body["analysis_job_id"] is not None
        assert body["duplicate_of_video_id"] is None

    def test_아직_끝나지_않은_동일_내용은_중복이_아니다(self, client):
        """`queued`·`running` 인 것을 빌리면 안 끝난 결과를 답으로 준다."""
        user_id = uuid4()
        self._seed_prior(user_id, status="queued")

        key = _issue(client, user_id)
        put_object(key, SIZE_OK, content_hash=self.HASH)

        res = _register(client, user_id, key)
        body = res.json()
        assert body["analysis_job_id"] is not None
        assert body["duplicate_of_video_id"] is None


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
            _register_clip(client, user_id)

        res = client.get(f"{V1}/videos", headers=_headers(mine))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_반려_사유가_목록에도_온다(self, client):
        """`/videos` 화면이 반려 사유를 펼쳐 보여준다(플러터 설계 5.3)."""
        # 🔴 해상도는 2026-09-19 결정으로 더는 반려 사유가 아니다 — 길이 초과로 반려시킨다.
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        _register(client, user_id, key, duration_ms=MAX_DURATION_MS + 1)

        row = client.get(f"{V1}/videos", headers=_headers(user_id)).json()[0]
        assert row["passed"] is False
        assert "길이" in row["reject_reason"]


def _register_clip(client, user_id):
    """등록하고 **그 자리에서 저장까지** 한다 — 이 파일의 다른 시험 대부분이
    바라는 것은 "쓸 수 있는 클립"이지 "아직 저장 안 한 임시분"이 아니다.

    🔴 작업이 생긴 클립은 등록만으로는 `kept=false` 다(미결 `jin` 24번 5조각
    해소, 2026-09-11) — `GET /videos`·공개 목록 어디에도 안 뜬다. 여기서
    `keep` 을 안 부르면 이 헬퍼를 쓰는 시험 대부분이 "방금 등록한 클립이
    목록에 없다"로 깨진다. 그 자체(등록만 하면 임시다)를 확인하는 시험은
    `TestRegisterVideo`·`TestKeepVideo`가 이 헬퍼를 안 쓰고 직접 부른다.
    """
    key = _issue(client, user_id)
    put_object(key, SIZE_OK)
    res = _register(client, user_id, key)
    assert res.status_code == 201, res.text
    video_id = res.json()["id"]
    kept = client.post(f"{V1}/videos/{video_id}/keep", headers=_headers(user_id))
    assert kept.status_code == 200, kept.text
    return video_id


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

    def test_저장_키는_안_실리고_업로더는_닉네임으로_실린다(self, client):
        owner = uuid4()
        register_nickname(owner, "업로더")
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
            "uploader_nickname",
            "uploader_card_slug",
            "width",
            "height",
        }
        # `_register`가 보내는 기본값(`paik` 15번) — 화면 비율이 실제로 실린다.
        assert (row["width"], row["height"]) == (1920, 1080)
        assert row["uploader_nickname"] == "업로더"
        assert row["uploader_card_slug"] is None

    def test_카드가_있으면_슬러그도_실린다(self, client):
        owner = uuid4()
        register_nickname(owner, "업로더")
        register_card_slug("owner-slug", owner)
        video_id = _register_clip(client, owner)
        client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_public": True},
            headers=_headers(owner),
        )
        row = client.get(f"{V1}/videos/public", headers=_headers(uuid4())).json()[0]
        assert row["uploader_card_slug"] == "owner-slug"

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


class TestFeatured:
    """「나를 보여주는 대표 영상」 (미결 `paik` 10번)."""

    def _feature(self, client, user_id, video_id):
        return client.patch(
            f"{V1}/videos/{video_id}",
            json={"is_featured": True},
            headers=_headers(user_id),
        )

    def test_대표로_세운다(self, client):
        user_id = uuid4()
        vid = _register_clip(client, user_id)
        res = self._feature(client, user_id, vid)
        assert res.status_code == 200, res.text
        assert res.json()["is_featured"] is True

    def test_대표는_사람당_하나_새로_세우면_옛것이_내려간다(self, client):
        user_id = uuid4()
        first = _register_clip(client, user_id)
        second = _register_clip(client, user_id)
        self._feature(client, user_id, first)
        self._feature(client, user_id, second)

        rows = {r["id"]: r["is_featured"]
                for r in client.get(f"{V1}/videos", headers=_headers(user_id)).json()}
        assert rows[first] is False
        assert rows[second] is True

    def test_내릴_수도_있다(self, client):
        user_id = uuid4()
        vid = _register_clip(client, user_id)
        self._feature(client, user_id, vid)
        res = client.patch(
            f"{V1}/videos/{vid}",
            json={"is_featured": False},
            headers=_headers(user_id),
        )
        assert res.status_code == 200, res.text
        assert res.json()["is_featured"] is False

    def test_반려된_클립은_대표로_못_세운다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        rejected = _register(
            client, user_id, key, duration_ms=MAX_DURATION_MS + 1
        ).json()
        assert rejected["passed"] is False

        res = self._feature(client, user_id, rejected["id"])
        assert res.status_code == 422
        assert error_code(res) == "CANNOT_FEATURE"

    def test_남의_클립은_대표로_못_세운다(self, client):
        owner, other = uuid4(), uuid4()
        vid = _register_clip(client, owner)
        res = self._feature(client, other, vid)
        assert res.status_code == 404


class TestFeaturedRead:
    """`GET /cards/{slug}/featured-video` — 남의 대표 영상 (미결 `paik` 10번)."""

    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/cards/some-slug/featured-video").status_code == 401

    def test_남의_대표를_카드_슬러그로_읽는다(self, client):
        owner, viewer = uuid4(), uuid4()
        vid = _register_clip(client, owner)
        client.patch(
            f"{V1}/videos/{vid}",
            json={"is_featured": True},
            headers=_headers(owner),
        )
        register_card_slug("hong-gildong-4f2a", owner)

        res = client.get(
            f"{V1}/cards/hong-gildong-4f2a/featured-video",
            headers=_headers(viewer),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["video_id"] == vid
        assert body["url"].startswith("https://")
        assert body["expires_in"] > 0

    def test_대표가_없으면_404_다(self, client):
        owner = uuid4()
        _register_clip(client, owner)  # 대표로 안 세움
        register_card_slug("no-featured-1a2b", owner)

        res = client.get(
            f"{V1}/cards/no-featured-1a2b/featured-video", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "NO_FEATURED_VIDEO"

    def test_없는_슬러그는_404_다(self, client):
        res = client.get(
            f"{V1}/cards/누구도-아님/featured-video", headers=_headers(uuid4())
        )
        assert res.status_code == 404
        assert error_code(res) == "NO_FEATURED_VIDEO"


class TestCardGrade:
    """`GET /cards/{slug}/grade` — 남의 표시 등급 (미결 `paik` 25·26번)."""

    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/cards/some-slug/grade").status_code == 401

    def test_없는_슬러그는_404_다(self, client):
        res = client.get(f"{V1}/cards/누구도-아님/grade", headers=_headers(uuid4()))
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"

    def test_대표_영상이_없으면_등급이_null이다(self, client):
        owner = uuid4()
        register_card_slug("no-report-1a2b", owner)  # 슬러그는 있지만 분석 없음

        res = client.get(
            f"{V1}/cards/no-report-1a2b/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["grade"] is None
        assert body["provisional"] is None

    def test_리뷰가_없는_A는_S가_아니라_그대로_온다(self, client):
        owner = uuid4()
        register_card_slug("grade-a-plain", owner)
        register_report_grade(owner, "A", provisional=False)

        res = client.get(
            f"{V1}/cards/grade-a-plain/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        assert res.json() == {"grade": "A", "provisional": False, "notes": None}

    def test_신뢰_우세인_A는_S로_오른다(self, client):
        owner = uuid4()
        register_card_slug("grade-a-trusted", owner)
        register_report_grade(owner, "A", provisional=False)
        register_trust_counts(owner, positive=4, total=4)  # 하한 0.510 > 0.5

        res = client.get(
            f"{V1}/cards/grade-a-trusted/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        assert res.json() == {"grade": "S", "provisional": False, "notes": None}

    def test_신뢰_우세_아닌_D는_F로_내려간다(self, client):
        owner = uuid4()
        register_card_slug("grade-d-plain", owner)
        register_report_grade(owner, "D", provisional=True)

        res = client.get(
            f"{V1}/cards/grade-d-plain/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        assert res.json() == {"grade": "F", "provisional": True, "notes": None}

    def test_provisional을_등급과_함께_내려준다(self, client):
        """26번 「하지 말 것」 — 등급 문자만 떼어 내보내지 않는다."""
        owner = uuid4()
        register_card_slug("grade-provisional", owner)
        register_report_grade(owner, "B", provisional=True)

        res = client.get(
            f"{V1}/cards/grade-provisional/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        assert res.json() == {"grade": "B", "provisional": True, "notes": None}

    def test_리포트_전체가_아니라_좁은_칸만_준다(self, client):
        """25번 「하지 말 것」 — 근거 문장·수치가 새면 안 된다.

        🔴 **2026-09-17에 칸이 하나 늘었다**(`notes`, `paik` 33번). 제기자가
        25번의 판단을 **스스로 정정했다** — "그때는 등급만 필요했습니다. 지금은
        문장도 필요합니다. 다만 리포트를 통째로 여는 것은 여전히 반대입니다."
        그래서 **항목별 점수·수치·근거(evidence)는 여전히 안 샌다** — 그것이
        이 검사가 지키는 선이고, 늘어난 칸은 카드용 불릿뿐이다.
        """
        owner = uuid4()
        register_card_slug("grade-narrow", owner)
        register_report_grade(owner, "C", provisional=False)

        res = client.get(
            f"{V1}/cards/grade-narrow/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        assert set(res.json()) == {"grade", "provisional", "notes"}

    def test_카드_불릿이_있으면_함께_온다(self, client):
        """`paik` 33번 — 추천 판이 「왜 이 사람인가」를 쓸 문장이다."""
        owner = uuid4()
        register_card_slug("grade-with-notes", owner)
        register_report_grade(owner, "B", provisional=False)
        register_card_notes(owner, ["차는 다리를 끝까지 뻗습니다"])

        res = client.get(
            f"{V1}/cards/grade-with-notes/grade", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        # 🔴 **한 줄뿐인 것이 정상이다** — 두 줄을 채우려고 지어내지 않는다.
        assert res.json()["notes"] == ["차는 다리를 끝까지 뻗습니다"]

    def test_옛_봉투로_적재된_리포트는_불릿이_null_이다(self, client):
        """🔴 `null` 은 「분석이 없다」가 아니라 「그 칸이 없는 봉투였다」이다."""
        owner = uuid4()
        register_card_slug("grade-no-notes", owner)
        register_report_grade(owner, "B", provisional=False)

        res = client.get(
            f"{V1}/cards/grade-no-notes/grade", headers=_headers(uuid4())
        )
        assert res.json()["notes"] is None
        assert res.json()["grade"] == "B"


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


class TestVideoLimit:
    """**갈래마다** 저장된(`kept=true`) 영상 개수 상한 — 2026-09-22, 사용자 요청.

    갈래는 화면의 두 탭과 같다 — 분석 영상(`analysis_job_id` 있음) / 업로드
    영상(없음). **합쳐서 3개가 아니라 3+3 이다.** 그 경계를 여기서 고정한다.
    """

    def _fill_uploaded(self, client, user_id, *, n=1):
        """업로드 갈래를 채운다. `analyze=False` 는 작업이 안 생겨 **등록하는
        순간 `kept=true`** 이고 `analysis_job_id` 가 없다.
        """
        ids = []
        for _ in range(n):
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            res = _register(client, user_id, key, analyze=False)
            assert res.status_code == 201, res.text
            assert res.json()["kept"] is True
            assert res.json()["analysis_job_id"] is None
            ids.append(res.json()["id"])
        return ids

    def _fill_analyzed(self, client, user_id, *, n=1):
        """분석 갈래를 채운다. 등록만으로는 `kept=false` 라 `keep` 까지 부른다."""
        ids = []
        for _ in range(n):
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            res = _register(client, user_id, key)
            assert res.status_code == 201, res.text
            assert res.json()["analysis_job_id"] is not None
            video_id = res.json()["id"]
            kept = client.post(
                f"{V1}/videos/{video_id}/keep", headers=_headers(user_id)
            )
            assert kept.status_code == 200, kept.text
            ids.append(video_id)
        return ids

    def _upload_url(self, client, user_id, **kw):
        body = {
            "content_type": "video/mp4",
            "size_bytes": SIZE_OK,
            "filename": "c.mp4",
        }
        body.update(kw)
        return client.post(
            f"{V1}/videos/upload-url", json=body, headers=_headers(user_id)
        )

    # --- 갈래가 서로를 안 막는다 (이 항목의 핵심) ---

    def test_분석_갈래가_차도_업로드는_된다(self, client):
        user_id = uuid4()
        self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        assert len(self._fill_uploaded(client, user_id, n=1)) == 1

    def test_업로드_갈래가_차도_분석은_된다(self, client):
        user_id = uuid4()
        self._fill_uploaded(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        assert len(self._fill_analyzed(client, user_id, n=1)) == 1

    def test_한_계정이_갈래마다_상한까지_가질_수_있다(self, client):
        """합치면 3 + 3 = 6 이다."""
        user_id = uuid4()
        self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        self._fill_uploaded(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        mine = client.get(f"{V1}/videos", headers=_headers(user_id)).json()
        assert len(mine) == MAX_VIDEOS_PER_GROUP * 2
        analyzed = [v for v in mine if v["analysis_job_id"] is not None]
        assert len(analyzed) == MAX_VIDEOS_PER_GROUP

    # --- 갈래마다 실제로 막힌다 ---

    def test_업로드_갈래가_차면_등록이_막힌다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        self._fill_uploaded(client, user_id, n=MAX_VIDEOS_PER_GROUP)

        res = _register(client, user_id, key, analyze=False)
        assert res.status_code == 422
        assert error_code(res) == "VIDEO_LIMIT_EXCEEDED"
        assert "업로드 영상" in res.json()["error"]["message"]

    def test_분석_갈래가_차면_등록이_막힌다(self, client):
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)

        res = _register(client, user_id, key)
        assert res.status_code == 422
        assert error_code(res) == "VIDEO_LIMIT_EXCEEDED"
        assert "분석 영상" in res.json()["error"]["message"]

    def test_반려된_클립은_업로드_갈래를_차지한다(self, client):
        """반려는 분석 작업이 안 생기므로 업로드 탭에 선다(화면과 같은 기준)."""
        user_id = uuid4()
        for _ in range(MAX_VIDEOS_PER_GROUP):
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            res = _register(client, user_id, key, duration_ms=MAX_DURATION_MS + 1)
            assert res.status_code == 201
            assert res.json()["passed"] is False
            assert res.json()["analysis_job_id"] is None

        # 업로드 갈래는 찼고 —
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        blocked = _register(client, user_id, key, analyze=False)
        assert blocked.status_code == 422
        assert error_code(blocked) == "VIDEO_LIMIT_EXCEEDED"
        # — 분석 갈래는 비어 있다
        assert len(self._fill_analyzed(client, user_id, n=1)) == 1

    def test_상한이어도_반려로_기록하지_않는다(self, client):
        """반려로 남기면 그 행이 **또 한 자리**를 차지한다."""
        user_id = uuid4()
        key = _issue(client, user_id)
        put_object(key, SIZE_OK)
        self._fill_uploaded(client, user_id, n=MAX_VIDEOS_PER_GROUP)

        res = _register(client, user_id, key, duration_ms=MAX_DURATION_MS + 1)
        assert res.status_code == 422
        assert error_code(res) == "VIDEO_LIMIT_EXCEEDED"

        mine = client.get(f"{V1}/videos", headers=_headers(user_id)).json()
        assert len(mine) == MAX_VIDEOS_PER_GROUP

    # --- 업로드 URL 발급 (헛걸음 줄이기) ---

    def test_analyze_를_주면_그_갈래로_미리_막는다(self, client):
        user_id = uuid4()
        self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)

        blocked = self._upload_url(client, user_id, analyze=True)
        assert blocked.status_code == 422
        assert error_code(blocked) == "VIDEO_LIMIT_EXCEEDED"
        # 안 찬 갈래를 주면 그대로 내준다
        assert self._upload_url(client, user_id, analyze=False).status_code == 200

    def test_analyze_를_안_주면_한쪽만_찼을_때는_안_막는다(self, client):
        """🔴 모를 때 막으면 **안 찬 갈래로 올리려는 사람을 잘못 막는다.**"""
        user_id = uuid4()
        self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        assert self._upload_url(client, user_id).status_code == 200

    def test_analyze_를_안_줘도_양쪽이_다_차면_막는다(self, client):
        user_id = uuid4()
        self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        self._fill_uploaded(client, user_id, n=MAX_VIDEOS_PER_GROUP)

        res = self._upload_url(client, user_id)
        assert res.status_code == 422
        assert error_code(res) == "VIDEO_LIMIT_EXCEEDED"

    # --- 저장(keep) 관문 ---

    def test_저장할_때도_갈래마다_막는다(self, client):
        """🔴 불변식 자리다. 자리가 있을 때 등록된 임시 클립 여럿이 **나중에
        한꺼번에** 저장되면 앞의 두 관문을 다 통과하고도 상한을 넘는다.
        """
        user_id = uuid4()
        ids = []
        for _ in range(MAX_VIDEOS_PER_GROUP + 1):
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            ids.append(_register(client, user_id, key).json()["id"])

        for video_id in ids[:MAX_VIDEOS_PER_GROUP]:
            res = client.post(
                f"{V1}/videos/{video_id}/keep", headers=_headers(user_id)
            )
            assert res.status_code == 200, res.text

        res = client.post(f"{V1}/videos/{ids[-1]}/keep", headers=_headers(user_id))
        assert res.status_code == 422
        assert error_code(res) == "VIDEO_LIMIT_EXCEEDED"
        assert "분석 영상" in res.json()["error"]["message"]

    def test_상한이어도_이미_저장된_것을_다시_저장하면_200_이다(self, client):
        """`keep` 은 멱등이다 — 자기 자신 때문에 막히면 안 된다."""
        user_id = uuid4()
        ids = self._fill_analyzed(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        res = client.post(f"{V1}/videos/{ids[0]}/keep", headers=_headers(user_id))
        assert res.status_code == 200, res.text
        assert res.json()["kept"] is True

    # --- 자리를 비우는 길 ---

    def test_지우면_그_갈래의_자리가_빈다(self, client):
        user_id = uuid4()
        ids = self._fill_uploaded(client, user_id, n=MAX_VIDEOS_PER_GROUP)
        assert (
            client.delete(
                f"{V1}/videos/{ids[0]}", headers=_headers(user_id)
            ).status_code
            == 204
        )
        assert len(self._fill_uploaded(client, user_id, n=1)) == 1

    def test_남의_영상은_내_자리를_안_차지한다(self, client):
        other = uuid4()
        self._fill_uploaded(client, other, n=MAX_VIDEOS_PER_GROUP)
        self._fill_analyzed(client, other, n=MAX_VIDEOS_PER_GROUP)

        mine = uuid4()
        assert len(self._fill_uploaded(client, mine, n=1)) == 1

    def test_임시_클립은_자리를_안_차지한다(self, client):
        """분석 중(`kept=false`)인 클립은 화면에도 안 보이고 스윕이 걷어 간다."""
        user_id = uuid4()
        for _ in range(MAX_VIDEOS_PER_GROUP + 2):
            key = _issue(client, user_id)
            put_object(key, SIZE_OK)
            res = _register(client, user_id, key)
            assert res.status_code == 201, res.text
            assert res.json()["kept"] is False


class TestVideoPoster:
    """카드에 깔 **한 장면**(JPEG) — `GET /videos/{id}/poster`.

    🔴 **`ffmpeg` 을 시험에서 돌리지 않는다.** 바깥 망으로 나가고 프로세스를
    띄우는 일이라, 여기서 재는 것은 **권한·캐시·에러 코드**뿐이다.

    🔴 **`conftest.py` 를 안 건드린다**(`fastapi/CLAUDE.md` 의 공유 파일).
    대신 provider 모듈의 객체를 갈아끼운다 — 그 provider 가 호출 시점에 읽는다.
    """

    @pytest.fixture
    def poster(self, monkeypatch):
        from app.analysis.adapter.outbound.stub.poster_stub import (
            MemoryPosterCache,
            StubPoster,
        )
        from app.analysis.dependencies import video_providers

        stub = StubPoster()
        monkeypatch.setattr(video_providers, "_POSTER", stub)
        monkeypatch.setattr(video_providers, "_POSTER_CACHE", MemoryPosterCache())
        return stub

    def test_인증이_필요하다(self, client, poster):
        assert client.get(f"{V1}/videos/{uuid4()}/poster").status_code == 401

    def test_공개_클립은_남도_장면을_받는다(self, client, poster):
        owner, viewer = uuid4(), uuid4()
        video_id = _register_clip(client, owner)
        client.patch(
            f"{V1}/videos/{video_id}", json={"is_public": True}, headers=_headers(owner)
        )

        res = client.get(f"{V1}/videos/{video_id}/poster", headers=_headers(viewer))

        assert res.status_code == 200, res.text
        assert res.headers["content-type"] == "image/jpeg"
        assert res.content.startswith(b"\xff\xd8")  # JPEG 머리

    def test_비공개_남의_클립은_404_다(self, client, poster):
        """🔴 **캐시보다 권한이 먼저다.** 뒤에 두면 한 번 떠 둔 비공개 클립의
        장면이 아무에게나 나간다."""
        owner, viewer = uuid4(), uuid4()
        video_id = _register_clip(client, owner)  # 비공개

        res = client.get(f"{V1}/videos/{video_id}/poster", headers=_headers(viewer))

        assert res.status_code == 404
        assert res.json()["error"]["code"] == "VIDEO_NOT_FOUND"
        assert poster.calls == 0, "권한이 없는데 떴다"

    def test_두_번_불러도_한_번만_뜬다(self, client, poster):
        """🔴 **이 캐시가 이 설계의 전부다** — 뜨는 일 자체는 여전히 비싸다."""
        owner = uuid4()
        video_id = _register_clip(client, owner)

        for _ in range(3):
            res = client.get(f"{V1}/videos/{video_id}/poster", headers=_headers(owner))
            assert res.status_code == 200, res.text

        assert poster.calls == 1

    def test_장면을_못_뜨면_404_다(self, client, monkeypatch):
        """형식을 못 읽거나 너무 짧은 영상이 있다 — 서버 오류가 아니다."""
        from app.analysis.adapter.outbound.stub.poster_stub import (
            MemoryPosterCache,
            StubPoster,
        )
        from app.analysis.dependencies import video_providers

        monkeypatch.setattr(video_providers, "_POSTER", StubPoster(jpeg=None))
        monkeypatch.setattr(video_providers, "_POSTER_CACHE", MemoryPosterCache())

        owner = uuid4()
        video_id = _register_clip(client, owner)

        res = client.get(f"{V1}/videos/{video_id}/poster", headers=_headers(owner))

        assert res.status_code == 404
        assert res.json()["error"]["code"] == "POSTER_NOT_AVAILABLE"
