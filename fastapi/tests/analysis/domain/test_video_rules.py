"""analysis/domain/rules/video_rules.py — 규격 판단. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from uuid import uuid4

from app.analysis.domain.rules.video_rules import (
    MAX_BYTES,
    MAX_DURATION_MS,
    build_storage_key,
    extension_for,
    owns_key,
    reject_reason,
)


def _ok(**kw):
    values = {
        "duration_ms": 10_000,
        "width": 1920,
        "height": 1080,
        "size_bytes": 50 * 1024 * 1024,
    }
    values.update(kw)
    return values


class TestRejectReason:
    def test_상한_안이면_사유가_없다(self):
        assert reject_reason(**_ok()) is None

    def test_상한값_자체는_통과한다(self):
        """경계에서 반려하면 "1080p 까지"라고 적어 둔 문서와 어긋난다."""
        assert (
            reject_reason(
                **_ok(
                    duration_ms=MAX_DURATION_MS,
                    size_bytes=MAX_BYTES,
                    width=1920,
                    height=1080,
                )
            )
            is None
        )

    def test_용량이_넘으면_사유에_MB_가_들어간다(self):
        reason = reject_reason(**_ok(size_bytes=MAX_BYTES + 1))
        assert reason is not None and "용량" in reason

    def test_길이가_넘으면_사유에_초가_들어간다(self):
        reason = reject_reason(**_ok(duration_ms=MAX_DURATION_MS + 1))
        assert reason is not None and "길이" in reason

    def test_4K_는_해상도로_반려된다(self):
        """4K 는 host RAM 이 먼저 터진다 — 미결 `ho` 9번의 실측."""
        reason = reject_reason(**_ok(width=3840, height=2160))
        assert reason is not None and "3840x2160" in reason

    def test_사유는_하나만_돌려준다(self):
        """전부 위반해도 문장은 하나다. 모아 붙이면 화면에서 안 읽힌다."""
        reason = reject_reason(
            duration_ms=MAX_DURATION_MS + 1,
            width=3840,
            height=2160,
            size_bytes=MAX_BYTES + 1,
        )
        assert reason is not None and reason.count("상한을 넘습니다") == 1


class TestContentType:
    def test_받는_형식만_확장자가_나온다(self):
        assert extension_for("video/mp4") == "mp4"
        assert extension_for("video/quicktime") == "mov"

    def test_모르는_형식은_None_이다(self):
        assert extension_for("video/x-msvideo") is None
        assert extension_for("image/png") is None


class TestStorageKey:
    def test_키에_업로더가_들어간다(self):
        user_id = uuid4()
        assert owns_key(user_id, build_storage_key(user_id, "mp4"))

    def test_남의_키는_대조에서_걸린다(self):
        """이 대조가 없으면 남이 올린 객체를 자기 영상으로 등록할 수 있다."""
        assert not owns_key(uuid4(), build_storage_key(uuid4(), "mp4"))

    def test_같은_사람이_두_번_받으면_다른_키다(self):
        user_id = uuid4()
        assert build_storage_key(user_id, "mp4") != build_storage_key(user_id, "mp4")
