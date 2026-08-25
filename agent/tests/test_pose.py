"""영상 디코딩·다운샘플링 검증.

모델을 올리지 않는 구간만 다룬다 — RT-DETR·ViTPose가 필요한
extract_keypoints는 GPU와 가중치가 있어야 하므로 여기서 검사하지 않는다.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from supersub_agent.pose import PoseResult, read_frames


def write_clip(path, n_frames: int, fps: float, size=(64, 48)) -> str:
    """프레임 번호를 화소값으로 새긴 테스트용 클립."""
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size
    )
    if not writer.isOpened():
        pytest.skip("MJPG 인코더를 쓸 수 없는 환경")
    for i in range(n_frames):
        frame = np.full((size[1], size[0], 3), i % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return str(path)


def test_sampled_fps_is_effective_not_target(tmp_path):
    """실효 샘플링 fps를 돌려준다 — 목표값을 그대로 담지 않는다.

    간격이 정수라 25fps에 target 15를 주면 step=round(1.67)=2가 되어
    실효 12.5fps다. 목표값 15를 기록하면 프레임→시각 환산이 20% 어긋난다.
    """
    clip = write_clip(tmp_path / "c.avi", n_frames=50, fps=25.0)

    frames, src_fps, sampled_fps = read_frames(clip, target_fps=15)

    assert src_fps == pytest.approx(25.0)
    assert sampled_fps == pytest.approx(12.5)
    assert sampled_fps != 15
    assert len(frames) == 25          # 50프레임을 2칸씩


def test_sampling_step_is_one_when_target_exceeds_source(tmp_path):
    """원본보다 높은 target을 줘도 프레임을 만들어내지 않는다."""
    clip = write_clip(tmp_path / "c.avi", n_frames=20, fps=10.0)

    frames, src_fps, sampled_fps = read_frames(clip, target_fps=30)

    assert sampled_fps == pytest.approx(src_fps)
    assert len(frames) == 20


def test_max_frames_caps_the_clip(tmp_path):
    clip = write_clip(tmp_path / "c.avi", n_frames=60, fps=30.0)

    frames, _, _ = read_frames(clip, target_fps=30, max_frames=10)

    assert len(frames) == 10


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_frames(tmp_path / "없는파일.mp4")


def test_frame_to_seconds_uses_effective_fps():
    """프레임 인덱스 → 시각 환산이 실효 fps를 따른다.

    12.5fps에서 44번 프레임은 3.52초다. 목표값 15를 쓰면 2.93초로 어긋난다.
    """
    result = PoseResult(
        keypoints=np.zeros((128, 17, 3)),
        frames=[],
        source_fps=25.0,
        sampled_fps=12.5,
    )

    assert result.frame_to_seconds(44) == pytest.approx(3.52)
    assert result.frame_to_seconds(0) == 0.0
