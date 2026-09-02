"""검수 오버레이(scripts/track_overlay.py) — 2패스 렌더링.

**ultralytics를 쓰지 않는다.** 그것은 AGPL 선택 의존성(`--extra tracking`)이라
기본 설치에 없고, 있어야만 도는 테스트를 만들면 CI에서 조용히 건너뛰게 된다.
추적 결과는 지어내고, 이 파일이 지키려는 것 — **프레임을 쌓지 않는 것**과
**박스가 맞는 프레임에 그려지는 것** — 만 본다.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import weakref
from pathlib import Path

import cv2
import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "track_overlay.py"
_spec = importlib.util.spec_from_file_location("track_overlay", SCRIPT)
track_overlay = importlib.util.module_from_spec(_spec)
sys.modules["track_overlay"] = track_overlay
_spec.loader.exec_module(track_overlay)


def _write_clip(path: Path, n: int = 24, w: int = 64, h: int = 48) -> Path:
    """프레임 번호가 밝기로 들어간 작은 영상. 순서 확인에 쓴다."""
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (w, h)
    )
    assert writer.isOpened(), "테스트용 인코더를 열 수 없다"
    for t in range(n):
        frame = np.full((h, w, 3), (t * 7) % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def _boxes(n: int, big: int = 1, small: int = 2) -> list[dict]:
    """big이 계속 크고, small은 잠깐만 더 커지는 추적 결과."""
    out = []
    for t in range(n):
        found = {big: (10.0, 10.0, 30.0, 30.0, 0.9)}
        if t < 3:                       # 잠깐 배경 인물이 더 크게 잡힌다
            found[small] = (0.0, 0.0, 60.0, 44.0, 0.8)
        out.append(found)
    return out


def test_subject_survives_a_briefly_bigger_bystander():
    """프레임 합계로 고르므로 잠깐 큰 인물에 대상이 넘어가지 않는다.

    pose.py는 프레임마다 가장 큰 박스를 고르는데, 이 도구는 한 번 정한 대상을
    클립 내내 유지한다 — 그 차이가 여기서 갈린다.
    """
    assert track_overlay.pick_subject(_boxes(24)) == 1


def test_pick_subject_returns_none_when_nothing_tracked():
    assert track_overlay.pick_subject([{}, {}]) is None


def test_render_draws_every_tracked_frame(tmp_path, monkeypatch):
    src = _write_clip(tmp_path / "in.mp4", n=24)
    per_frame = _boxes(24)
    monkeypatch.setattr(track_overlay, "track_people", lambda *a, **k: per_frame)

    out = tmp_path / "out.mp4"
    info = track_overlay.render(src, out, "unused.pt", 0.4, trail=5)

    assert info["subject"] == 1
    assert info["frames"] == info["tracked"] == 24, "프레임이 잘리면 안 된다"
    assert info["subject_seen"] == 24
    assert info["size"] == (64, 48)

    cap = cv2.VideoCapture(str(out))
    written = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    assert written == 24


def test_track_people_does_not_hand_back_frames():
    """2패스의 존재 이유를 **계약으로** 지킨다.

    예전 구현은 `(per_frame, frames)`를 돌려줬고, 그래서 RAM이 클립 길이에
    비례했다 — 4K 92프레임에 최대 RSS 3.9GB, 30초(750프레임)면 20GB다.
    프레임을 다시 실어 나르기 시작하면 이 테스트가 먼저 깨진다.

    바이트를 세지 않는 이유: cv2 할당은 파이썬 할당자 밖이라 tracemalloc이
    못 보고, RSS는 프로세스 최고치라 한 프로세스 안에서 비교가 안 된다.
    실제 메모리는 4K 클립으로 따로 쟀다(커밋 메시지 참고).
    """
    src = inspect.getsource(track_overlay.track_people)
    assert "return per_frame" in src
    assert "frames" not in src.split('"""')[-1], "프레임을 다시 모으고 있다"

    sig = inspect.signature(track_overlay.render)
    assert "per_frame = track_people" in inspect.getsource(track_overlay.render), (
        "render가 track_people의 단일 반환값을 받아야 한다"
    )
    assert list(sig.parameters) == ["video", "out_path", "model_name", "conf", "trail"]


def test_render_reads_each_frame_once_and_keeps_none(tmp_path, monkeypatch):
    """렌더 루프가 프레임을 붙들지 않는다 — 읽은 만큼만 쓰고 넘어간다."""
    n = 24
    src = _write_clip(tmp_path / "in.mp4", n=n)
    monkeypatch.setattr(track_overlay, "track_people", lambda *a, **k: _boxes(n))

    refs: list[weakref.ref] = []
    peak = 0
    real_read = cv2.VideoCapture.read

    def counting_read(self):
        nonlocal peak
        ok, frame = real_read(self)
        if ok:
            refs.append(weakref.ref(frame))
            peak = max(peak, sum(1 for r in refs if r() is not None))
        return ok, frame

    monkeypatch.setattr(cv2.VideoCapture, "read", counting_read)
    info = track_overlay.render(src, tmp_path / "out.mp4", "unused.pt", 0.4, 5)

    assert info["frames"] == n
    assert len(refs) == n, "프레임마다 정확히 한 번 읽는다"
    # 2는 정상이다: 방금 읽은 것과, 루프 변수가 아직 재바인딩되지 않은 직전 것.
    assert peak <= 2, f"렌더 루프가 프레임을 붙들고 있다 (동시 생존 {peak}장)"


def test_render_reports_truncation_instead_of_misaligning(tmp_path, monkeypatch):
    """추적이 본 것보다 영상이 짧으면 뒤를 자르고 그 사실을 남긴다.

    박스와 프레임을 한 칸씩 맞춰 소비하므로 앞쪽 정렬은 유지된다. 조용히
    넘어가면 "왜 뒤가 없지"를 다음 사람이 다시 조사하게 된다.
    """
    src = _write_clip(tmp_path / "in.mp4", n=10)
    monkeypatch.setattr(track_overlay, "track_people", lambda *a, **k: _boxes(24))

    info = track_overlay.render(src, tmp_path / "out.mp4", "unused.pt", 0.4, 5)

    assert info["tracked"] == 24
    assert info["frames"] == 10
    assert info["frames"] != info["tracked"], "main()이 이 차이를 경고로 알린다"


def test_render_rejects_an_unreadable_video(tmp_path, monkeypatch):
    monkeypatch.setattr(track_overlay, "track_people", lambda *a, **k: _boxes(4))
    with pytest.raises(ValueError, match="열 수 없습니다"):
        track_overlay.render(
            tmp_path / "없는파일.mp4", tmp_path / "out.mp4", "unused.pt", 0.4, 5
        )
