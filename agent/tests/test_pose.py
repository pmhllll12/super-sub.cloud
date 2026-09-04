"""영상 디코딩·다운샘플링 검증.

모델을 올리지 않는 구간만 다룬다 — RT-DETR·ViTPose가 필요한
extract_keypoints는 GPU와 가중치가 있어야 하므로 여기서 검사하지 않는다.
"""

from __future__ import annotations

import base64
import logging
import math

import cv2
import numpy as np
import pytest

from supersub_agent import pose
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


# --- 분석 창은 초로 정한다 (미결 7번 「인접 결함 두 건」) --------------------

def test_analysis_window_is_the_same_duration_across_source_fps(tmp_path):
    """**같은 실시간 길이를 본다** — 소스 fps가 달라도.

    프레임 수로만 막으면 300장이 30fps에서 10.0초, 24fps에서 12.5초가 되어
    같은 동작의 두 인코딩이 서로 다른 구간을 분석하게 된다. 그 차이는 아무
    데도 기록되지 않는다.
    """
    seen = {}
    for fps in (24.0, 25.0, 30.0):
        clip = write_clip(tmp_path / f"c{int(fps)}.avi", n_frames=int(fps * 6), fps=fps)
        frames, _, sampled = read_frames(clip, target_fps=30, max_seconds=2.0)
        seen[fps] = len(frames) / sampled          # 실제로 덮은 초

    for fps, covered in seen.items():
        assert covered == pytest.approx(2.0, abs=0.05), f"{fps}fps 에서 {covered}초"


def test_seconds_budget_keeps_frame_count_proportional_to_fps(tmp_path):
    """초로 막으면 장수는 fps에 비례한다 — 24fps 2초는 48장, 30fps 2초는 60장."""
    c24 = write_clip(tmp_path / "a.avi", n_frames=200, fps=24.0)
    c30 = write_clip(tmp_path / "b.avi", n_frames=200, fps=30.0)

    assert len(read_frames(c24, target_fps=30, max_seconds=2.0)[0]) == 48
    assert len(read_frames(c30, target_fps=30, max_seconds=2.0)[0]) == 60


def test_ntsc_fps_does_not_lose_a_frame_at_the_boundary(tmp_path):
    """29.97fps·10초에서 300장이다 — 299장이 아니다.

    예산을 내림으로 잡으면 29.97 × 10 = 299.7 → 299장이 되어 **기존 동작이
    조용히 한 장 줄어든다.** NTSC 소스가 평가셋의 절반이라 경계가 실제로 걸린다.
    """
    clip = write_clip(tmp_path / "c.avi", n_frames=300, fps=29.97)

    frames, _, _ = read_frames(clip, target_fps=30, max_seconds=10.0)

    assert len(frames) == 300


def test_frame_cap_still_guards_memory_when_seconds_budget_is_larger(tmp_path):
    """실효 fps가 목표를 넘으면 초 예산이 프레임 예산을 넘어선다 — 가드가 이긴다.

    40fps에 target 30을 주면 step=round(1.33)=1이라 실효 40fps다. 10초면
    400장이 되어 미결 9번(host RAM)의 상한을 넘는다.
    """
    clip = write_clip(tmp_path / "c.avi", n_frames=400, fps=40.0)

    frames, _, sampled = read_frames(
        clip, target_fps=30, max_frames=300, max_seconds=10.0
    )

    assert sampled == pytest.approx(40.0)      # 목표를 넘는 실효 fps
    assert len(frames) == 300                  # 초 예산 400 이 아니라 가드 300


def test_low_effective_fps_warns(tmp_path, caplog):
    """절벽은 경고한다 — 다만 이 경고가 fps 불변성을 뜻하지는 않는다."""
    clip = write_clip(tmp_path / "c.avi", n_frames=20, fps=10.0)

    with caplog.at_level(logging.WARNING, logger="supersub_agent.pose"):
        read_frames(clip, target_fps=30)

    assert any("실효 샘플링 fps" in r.message for r in caplog.records)


@pytest.mark.parametrize("fps", [23.976, 24.0, 25.0, 29.97, 30.0])
def test_common_cinema_and_ntsc_fps_do_not_warn(tmp_path, caplog, fps):
    """흔한 소스는 경고하지 않는다 — **NTSC 24(23.976)를 포함해서.**

    한계를 목표의 80%(=24.0)로 두면 23.976이 아슬아슬하게 걸린다. 평가셋에
    실제로 있는 흔한 소스이고, 흔한 입력이 매번 경고를 내면 그 경고는 읽히지
    않게 된다.
    """
    clip = write_clip(tmp_path / "c.avi", n_frames=48, fps=fps)

    with caplog.at_level(logging.WARNING, logger="supersub_agent.pose"):
        read_frames(clip, target_fps=30)

    assert not [r for r in caplog.records if "실효 샘플링 fps" in r.message]


def test_unbounded_window_keeps_only_the_memory_guard(tmp_path):
    """`max_seconds=inf` 는 "창 제한 없음"이다 — 예전 동작(장수만)을 그대로 낸다."""
    clip = write_clip(tmp_path / "c.avi", n_frames=400, fps=30.0)

    frames, _, _ = read_frames(
        clip, target_fps=30, max_frames=300, max_seconds=math.inf
    )

    assert len(frames) == 300


def test_reload_uses_the_same_caps_as_extraction(tmp_path):
    """재디코딩이 추출과 **같은 장수**를 잘라야 한다.

    상한을 결과가 들고 다니지 않으면, 좁은 창으로 추출해 놓고 미리보기만
    기본값으로 다시 읽어 프레임이 키포인트보다 길어진다 — 인덱스가 어긋난다.
    """
    clip = write_clip(tmp_path / "c.avi", n_frames=200, fps=30.0)
    frames, src, sampled = read_frames(clip, target_fps=30, max_seconds=2.0)

    result = PoseResult(
        keypoints=np.zeros((len(frames), 17, 3)),
        source_fps=src,
        sampled_fps=sampled,
        video_path=clip,
        target_fps=30,
        max_seconds=2.0,
    )

    assert len(result.load_frames()) == len(frames) == 60


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
        source_fps=25.0,
        sampled_fps=12.5,
    )

    assert result.frame_to_seconds(44) == pytest.approx(3.52)
    assert result.frame_to_seconds(0) == 0.0


# ── 프레임은 보관하지 않고 렌더링 시점에 다시 디코딩한다 ────────────────────
#
# 프레임은 채점에 쓰이지 않는다(extract_features는 키포인트와 도구 궤적만
# 받는다). 쓰이는 곳은 판정이 끝난 뒤의 미리보기뿐인데, 그때까지 4K 300장을
# 들고 있으면 판정 모델과 메모리가 겹친다. 재디코딩이 원본과 **같은 프레임**을
# 준다는 것이 이 교체의 전제이므로 여기서 지킨다.

def test_pose_result_does_not_hold_frames():
    """결과가 프레임을 들고 다니면 안 된다 — 계약이 되돌아가는 것을 막는다."""
    result = PoseResult(keypoints=np.zeros((2, 17, 3)), source_fps=30.0, sampled_fps=15.0)

    assert not hasattr(result, "frames")


def test_load_frames_reproduces_the_original_decode(tmp_path):
    """재디코딩이 추출 때 본 프레임과 화소까지 같아야 한다."""
    clip = write_clip(tmp_path / "c.avi", n_frames=12, fps=30.0)
    original, _, sampled_fps = read_frames(clip, target_fps=15)

    result = PoseResult(
        keypoints=np.zeros((len(original), 17, 3)), source_fps=30.0,
        sampled_fps=sampled_fps, video_path=clip, target_fps=15,
    )
    reloaded = result.load_frames()

    assert len(reloaded) == len(original)
    assert all(np.array_equal(a, b) for a, b in zip(original, reloaded))


def test_load_frames_uses_the_recorded_target_fps(tmp_path):
    """추출 때 쓴 target_fps로 다시 골라야 한다 — 다른 값이면 다른 프레임이다."""
    clip = write_clip(tmp_path / "c.avi", n_frames=12, fps=30.0)
    kps = np.zeros((12, 17, 3))

    dense = PoseResult(keypoints=kps, source_fps=30.0, sampled_fps=30.0,
                       video_path=clip, target_fps=30).load_frames()
    sparse = PoseResult(keypoints=kps, source_fps=30.0, sampled_fps=15.0,
                        video_path=clip, target_fps=15).load_frames()

    assert len(dense) == 12
    assert len(sparse) == 6


def test_load_frames_is_none_without_a_video():
    """합성 키포인트 경로에는 영상이 없다 — 미리보기 없이 채점만 한다."""
    result = PoseResult(keypoints=np.zeros((3, 17, 3)), source_fps=30.0, sampled_fps=15.0)

    assert result.load_frames() is None


# --- 분석 대상 지정 (미결 18번) ---------------------------------------------


def test_iou_is_zero_when_boxes_do_not_touch():
    assert pose._iou((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0


def test_iou_of_identical_boxes_is_one():
    assert pose._iou((3, 4, 10, 20), (3, 4, 10, 20)) == pytest.approx(1.0)


def test_anchor_frame_snaps_to_the_grid_and_reports_the_gap():
    """지정 시각이 격자에 없을 수 있다 — 붙이되 **어긋난 정도를 돌려준다.**"""
    frame, offset, clamped = pose.anchor_frame_for(1040.0, 12.5, 100)

    assert frame == 13                       # 1.04초 × 12.5fps = 13.0
    assert offset == 0.0
    assert clamped is False

    frame, offset, clamped = pose.anchor_frame_for(1000.0, 12.5, 100)
    assert frame == 13                       # 12.5 → 가장 가까운 13
    assert offset == pytest.approx(0.5)
    assert clamped is False


def test_anchor_outside_the_analysis_window_is_clamped_and_says_so():
    """업로드 상한 60초 대 분석 창 10초 — 35초 지점은 창에 아예 없다.

    🔴 조용히 당기면 사용자는 자기가 찍은 순간이 분석된 줄 안다.
    """
    frame, _, clamped = pose.anchor_frame_for(35_000.0, 30.0, 300)

    assert frame == 299
    assert clamped is True


def test_anchor_needs_a_known_grid():
    """모르는 격자에서 프레임을 지어내지 않는다 (E-3와 같은 규약)."""
    with pytest.raises(ValueError):
        pose.anchor_frame_for(1000.0, 0.0, 100)


def _auto(n, box=(0.0, 0.0, 30.0, 40.0)):
    return [box] * n


def test_no_specification_returns_the_very_same_list():
    """🔴 지정이 없으면 **같은 객체를 그대로** 돌려준다.

    목록을 새로 만들면 언젠가 값이 달라질 여지가 생긴다. 지정이 없을 때
    ViTPose 입력이 한 비트도 달라지지 않아야 기존 평가(B-1~B-6)와 비교가
    끊기지 않는다.
    """
    auto = _auto(5)
    boxes, selection = pose.select_subject_boxes(auto, [[]] * 5, None, 30.0, (64, 48))

    assert boxes is auto
    assert selection.source == "auto"
    assert selection.anchor_frame is None


def test_specification_picks_the_overlapping_candidate_not_the_largest():
    """찍은 사람이 가장 큰 사람이 아닐 수 있다 — 그게 이 기능의 존재 이유다."""
    big = (0.0, 0.0, 60.0, 40.0)        # 자동 선택이 고르는 큰 사람
    small = (60.0, 0.0, 20.0, 40.0)     # 사용자가 찍은 작은 사람
    n = 4
    boxes, selection = pose.select_subject_boxes(
        _auto(n, big), [[big, small]] * n,
        pose.SubjectRequest(box=(0.6, 0.0, 0.2, 1.0), at_ms=0.0),
        30.0, (100, 40),
    )

    assert selection.source == "specified"
    assert selection.anchor_frame == 0
    assert boxes == [small] * n, "닻에서 앞뒤로 같은 사람을 이어가야 한다"


def test_specification_propagates_backwards_from_a_late_anchor():
    """드래그는 한 프레임인데 분석은 전 프레임이다 — 앞쪽도 채워야 한다."""
    a = (0.0, 0.0, 20.0, 40.0)
    b = (50.0, 0.0, 20.0, 40.0)
    n = 6
    boxes, selection = pose.select_subject_boxes(
        _auto(n, a), [[a, b]] * n,
        # 마지막 프레임에서 b를 찍었다 (30fps에서 5프레임 = 166.7ms)
        pose.SubjectRequest(box=(0.5, 0.0, 0.2, 1.0), at_ms=166.7),
        30.0, (100, 40),
    )

    assert selection.anchor_frame == 5
    assert boxes == [b] * n


def test_a_miss_falls_back_to_auto_and_says_why():
    """🔴 조용히 떨어지지 않는다. 사용자는 자기가 찍은 대로 분석된 줄 안다."""
    here = (0.0, 0.0, 20.0, 40.0)
    n = 3
    auto = _auto(n, here)
    boxes, selection = pose.select_subject_boxes(
        auto, [[here]] * n,
        # 화면 반대편을 찍었다 — 겹치는 후보가 없다
        pose.SubjectRequest(box=(0.8, 0.0, 0.2, 1.0), at_ms=0.0),
        30.0, (100, 40),
    )

    assert boxes is auto
    assert selection.source == "fallback"
    assert "못 찾았다" in selection.why
    assert selection.anchor_iou == 0.0


def test_continuity_breaks_are_counted_not_hidden():
    """후보가 사라진 프레임은 자동으로 떨어지고 **몇 번인지 남는다.**

    직전 박스를 계속 들고 가면 첫 매칭 오류를 그대로 굳힌다.
    """
    a = (0.0, 0.0, 20.0, 40.0)
    candidates = [[a], [], [a]]
    boxes, selection = pose.select_subject_boxes(
        [a, None, a], candidates,
        pose.SubjectRequest(box=(0.0, 0.0, 0.2, 1.0), at_ms=0.0),
        30.0, (100, 40),
    )

    assert selection.source == "specified"
    assert selection.continuity_breaks == 1
    assert boxes[1] is None, "끊긴 프레임은 자동 선택 결과를 그대로 쓴다"


def test_pixel_coordinates_are_rejected_not_clamped():
    """🔴 화면 픽셀을 그대로 보내면 **거부한다.**

    조용히 클램프하면 엉뚱한 사람을 분석하고도 "지정대로 했다"고 답한다.
    """
    with pytest.raises(ValueError, match="정규화"):
        pose.parse_subject_spec("745,380,225,410", 1000.0)


def test_a_box_without_a_time_is_rejected():
    with pytest.raises(ValueError, match="subject_at_ms"):
        pose.parse_subject_spec("0.1,0.1,0.2,0.3", None)


def test_no_box_means_auto():
    assert pose.parse_subject_spec(None, None) is None


def test_subject_envelope_normalizes_boxes_to_the_frontend_coordinate_system():
    result = pose.PoseResult(
        keypoints=np.zeros((2, 17, 3)), source_fps=30.0, sampled_fps=30.0,
        subject_boxes=[(50.0, 20.0, 25.0, 40.0), None],
        frame_size=(100, 80),
    )

    env = pose.subject_envelope(result, 2)

    assert env["known"] is True
    assert env["boxes"] == [[0.5, 0.25, 0.25, 0.5], None]
    assert env["frames_with_box"] == 1
    assert env["source"] == "auto"


def test_subject_envelope_admits_it_knows_nothing_on_the_synthetic_path():
    env = pose.subject_envelope(None, 12)

    assert env["known"] is False
    assert "합성" in env["why"]


def test_area_jump_counts_a_likely_identity_switch():
    """🔴 `continuity_breaks`가 못 잡는 실패를 이쪽이 센다.

    신원이 바뀔 때는 겹침이 넉넉해서 "끊김"으로 안 잡힌다. 실측
    (`3R1kvNrGJK0`)에서 타자 트랙이 심판으로 갈아탔을 때 끊김은 0이었고
    넓이는 2.5배 뛰었다.
    """
    small = (0.0, 0.0, 10.0, 10.0)
    big = (0.0, 0.0, 20.0, 20.0)        # 넓이 4배
    assert pose.count_area_jumps([small, small, big, big]) == 1


def test_area_jump_ignores_gradual_growth():
    """카메라로 다가오면 넓이는 실제로 커진다 — 그것까지 세면 신호가 죽는다."""
    boxes = [(0.0, 0.0, 10.0 + i, 10.0 + i) for i in range(10)]
    assert pose.count_area_jumps(boxes) == 0


def test_area_jump_skips_frames_without_a_box():
    """박스가 없는 프레임은 `continuity_breaks` 쪽 이야기다."""
    box = (0.0, 0.0, 10.0, 10.0)
    assert pose.count_area_jumps([box, None, box]) == 0
