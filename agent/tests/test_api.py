"""결과 봉투 — 프레임 단위 값이 어느 격자 위에 있는지 (미결 7번 E-3).

`run_pipeline` 전체를 돌리려면 판정 모델이 필요하다. 여기서 재는 것은 봉투를
만드는 부분뿐이라 `build_timebase`만 떼어 본다.
"""
from __future__ import annotations

import numpy as np

from supersub_agent.api import build_timebase
from supersub_agent.pose import PoseResult


def pose_at(src_fps: float, sampled_fps: float, target_fps: int = 30) -> PoseResult:
    """격자만 있는 최소 PoseResult. 키포인트 값은 이 검사와 무관하다."""
    return PoseResult(
        keypoints=np.zeros((1, 17, 3)),
        source_fps=src_fps,
        sampled_fps=sampled_fps,
        target_fps=target_fps,
    )


def test_timebase_carries_the_grid_and_the_seconds():
    feats = {"impact_frame": 62, "follow_through_duration_frames": 8}
    # 25fps 소스에 target 30 → step 1, 실효 25fps.
    tb = build_timebase(feats, frame_count=250, pose=pose_at(25.0, 25.0))

    assert tb["known"] is True
    assert tb["source_fps"] == 25.0
    assert tb["sampled_fps"] == 25.0
    assert tb["step"] == 1
    assert tb["analyzed_seconds"] == 10.0
    assert tb["seconds"]["impact_frame"] == 2.48


def test_the_same_frame_number_is_a_different_moment_on_another_grid():
    """이 결함이 왜 결함인지가 이 검사다 — 번호만 보면 둘을 구분할 수 없다."""
    feats = {"impact_frame": 62}

    fast = build_timebase(feats, 300, pose_at(50.0, 25.0, target_fps=30))
    slow = build_timebase(feats, 150, pose_at(25.0, 12.5, target_fps=15))

    assert fast["seconds"]["impact_frame"] == 2.48
    assert slow["seconds"]["impact_frame"] == 4.96
    # 솎은 간격도 함께 나가야 어디서 갈렸는지 되짚을 수 있다.
    assert (fast["step"], slow["step"]) == (2, 2)


def test_synthetic_path_says_it_does_not_know_instead_of_guessing():
    """🔴 소스 영상이 없으면 초를 지어내지 않는다.

    예전 `run_pipeline(fps=12.0)` 기본값처럼 그럴듯한 수를 채워 넣는 것이
    이 결함이 생긴 방식이다.
    """
    tb = build_timebase({"impact_frame": 20}, frame_count=40, pose=None)

    assert tb["known"] is False
    assert "seconds" not in tb
    assert tb["frames"] == 40
    assert tb["why"]


def test_timebase_is_a_sibling_of_features_not_a_part_of_it():
    """`features`에 섞으면 판정 입력이 달라져 기존 평가와 비교가 끊긴다."""
    feats = {"impact_frame": 62, "follow_through_duration_frames": 8}
    before = dict(feats)

    build_timebase(feats, 250, pose_at(25.0, 25.0))

    assert feats == before
