"""영상 디코딩·다운샘플링 검증.

모델을 올리지 않는 구간만 다룬다 — RT-DETR·ViTPose가 필요한
extract_keypoints는 GPU와 가중치가 있어야 하므로 여기서 검사하지 않는다.
"""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest

from supersub_agent.pose import (
    PoseResult,
    crop_to_person,
    encode_preview,
    read_frames,
    stack_object_tracks,
)


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


def test_object_tracks_fill_missing_frames_with_zero_confidence():
    """미검출 프레임은 신뢰도 0으로 채운다 — 키포인트와 같은 규약."""
    per_frame = [
        {"sports_ball": (100.0, 200.0, 0.95)},
        {},
        {"sports_ball": (110.0, 205.0, 0.90)},
        {"sports_ball": (120.0, 210.0, 0.88)},
    ]

    tracks = stack_object_tracks(per_frame)

    assert set(tracks) == {"sports_ball"}
    ball = tracks["sports_ball"]
    assert ball.shape == (4, 3)
    assert ball[1].tolist() == [0.0, 0.0, 0.0]
    assert ball[0].tolist() == [100.0, 200.0, 0.95]


def test_never_confident_tool_is_dropped():
    """확실한 검출이 없는 도구는 궤적으로 남기지 않는다.

    축구·농구 클립 모두에서 tennis_racket 오검출은 0.8 이상 프레임이 0개였다
    (중앙값 0.45). 최고신뢰도만 보면 농구 쪽 0.67이 통과해 버린다.
    """
    per_frame = [
        {"sports_ball": (10.0, 10.0, 0.95), "tennis_racket": (1.0, 1.0, 0.45)},
        {"sports_ball": (12.0, 11.0, 0.91), "tennis_racket": (2.0, 1.0, 0.67)},
        {"sports_ball": (14.0, 12.0, 0.88), "tennis_racket": (3.0, 1.0, 0.52)},
    ]

    tracks = stack_object_tracks(per_frame)

    assert "sports_ball" in tracks
    assert "tennis_racket" not in tracks, "0.67은 통과시키면 안 된다"


def test_briefly_visible_but_confident_tool_is_kept():
    """짧게 보여도 확실하면 남긴다 — 찬 뒤 화면 밖으로 나가는 공."""
    per_frame = ([{}] * 20
                 + [{"sports_ball": (50.0, 50.0, 0.93)}] * 3
                 + [{}] * 20)

    tracks = stack_object_tracks(per_frame)

    assert "sports_ball" in tracks
    assert tracks["sports_ball"][20, 2] == 0.93


def test_object_detection_ratio():
    result = PoseResult(
        keypoints=np.zeros((4, 17, 3)),
        frames=[],
        source_fps=25.0,
        sampled_fps=12.5,
        objects={"sports_ball": np.array([
            [1.0, 1.0, 0.9], [0.0, 0.0, 0.0], [2.0, 2.0, 0.8], [0.0, 0.0, 0.0],
        ])},
    )

    assert result.object_detection_ratio("sports_ball") == pytest.approx(0.5)
    assert result.object_detection_ratio("없는도구") == 0.0


def _kps_at(x: float, y: float, spread: float = 40.0) -> np.ndarray:
    kps = np.zeros((17, 3))
    kps[:, 0] = x + np.linspace(-spread, spread, 17)
    kps[:, 1] = y + np.linspace(-spread, spread, 17)
    kps[:, 2] = 0.9
    return kps


def test_crop_to_person_follows_the_subject():
    """사람 주변만 잘라낸다 — 4K 전체를 축소하면 자세가 안 보인다."""
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    kps = _kps_at(1500.0, 300.0)

    cropped = crop_to_person(frame, kps)

    assert cropped.shape[0] < frame.shape[0]
    assert cropped.shape[1] < frame.shape[1]
    assert cropped.size > 0


def test_crop_falls_back_when_keypoints_are_missing():
    """유효 키포인트가 없으면 자르지 않고 원본을 준다."""
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    kps = np.zeros((17, 3))       # 전부 신뢰도 0

    assert crop_to_person(frame, kps).shape == frame.shape


def test_encode_preview_limits_width_and_is_a_data_uri():
    """4K 원본이 그대로 JSON에 실리지 않도록 폭을 제한한다."""
    frame = np.full((2160, 3840, 3), 120, dtype=np.uint8)

    uri = encode_preview(frame, max_width=720)

    assert uri.startswith("data:image/jpeg;base64,")
    raw = base64.b64decode(uri.split(",", 1)[1])
    decoded = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[1] == 720
    assert len(raw) < 400_000, "응답에 실을 수 있는 크기여야 한다"


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
