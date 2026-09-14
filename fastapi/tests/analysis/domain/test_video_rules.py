"""analysis/domain/rules/video_rules.py — 규격 판단. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from uuid import uuid4

from app.analysis.domain.rules.video_rules import (
    MAX_BYTES,
    MAX_DURATION_MS,
    MAX_LONG_SIDE,
    MAX_SHORT_SIDE,
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

    def test_4K는_이제_통과한다(self):
        """정정(2026-09-11) — `ho` 9번이 메모리 예산을 바이트로 옮기며 4K를
        이미 안전하다고 확정했는데(agent/eval/pending9_budget/), 이 상한이
        안 풀려 있었다. 가로·세로 둘 다 확인한다(방향 무관)."""
        assert reject_reason(**_ok(width=3840, height=2160)) is None  # 가로
        assert reject_reason(**_ok(width=2160, height=3840)) is None  # 세로

    def test_세로로_찍은_1080p는_이제_통과한다(self):
        """정정(2026-09-11) — 4K 와 무관한 별개 버그. 옛 상한이 `width`·
        `height` 를 그대로 비교해서, 화질은 그대로 1080p인 세로 영상
        (1080×1920, 스마트폰 기본 방향)이 방향만으로 반려됐었다."""
        assert reject_reason(**_ok(width=1080, height=1920)) is None

    def test_4K를_넘으면_여전히_반려된다(self):
        reason = reject_reason(**_ok(width=MAX_LONG_SIDE + 1, height=MAX_SHORT_SIDE))
        assert reason is not None and "해상도" in reason
        reason = reject_reason(**_ok(width=MAX_LONG_SIDE, height=MAX_SHORT_SIDE + 1))
        assert reason is not None and "해상도" in reason

    def test_analyze_false_면_해상도_상한을_안_본다(self):
        """해상도 상한은 분석 워커를 지키는 값이라 기록용 업로드엔 안 건다."""
        over = MAX_LONG_SIDE + 1
        assert reject_reason(**_ok(width=over, height=over, analyze=False)) is None

    def test_analyze_false_라도_용량과_길이는_본다(self):
        """용량·길이는 저장소·비용에 걸린 것이라 `analyze` 와 무관하다."""
        assert "용량" in reject_reason(**_ok(size_bytes=MAX_BYTES + 1, analyze=False))
        assert "길이" in reject_reason(
            **_ok(duration_ms=MAX_DURATION_MS + 1, analyze=False)
        )

    def test_사유는_하나만_돌려준다(self):
        """전부 위반해도 문장은 하나다. 모아 붙이면 화면에서 안 읽힌다."""
        reason = reject_reason(
            duration_ms=MAX_DURATION_MS + 1,
            width=MAX_LONG_SIDE + 1,
            height=MAX_SHORT_SIDE + 1,
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

    def test_닉네임과_원본이름이_키에_들어간다(self):
        """미결 jin 24번 — 콘솔에서 알아볼 수 있게."""
        user_id = uuid4()
        key = build_storage_key(
            user_id,
            "mp4",
            nickname="ㅇㄹㅇㄹ",
            original_filename="My Kick (final).mp4",
        )
        assert key.startswith(f"videos/{user_id}/ㅇㄹㅇㄹ-")
        assert "My-Kick-final" in key
        assert key.endswith(".mp4")
        assert owns_key(user_id, key)  # 접두사는 그대로라 소유 검사가 유지된다

    def test_이상한_문자와_빈_값도_안전하다(self):
        user_id = uuid4()
        key = build_storage_key(
            user_id, "mov", nickname="  ", original_filename="???.mov"
        )
        # 닉네임이 비면 user, 이름이 비면 clip 으로 떨어진다
        assert key.startswith(f"videos/{user_id}/user-clip-")
        assert key.endswith(".mov")
