"""서비스 입력 관측 계층 검증.

여기서 지키는 것은 두 가지다.

 1. 관측이 **정확한가** — 후보 수·집계·FPS·영속화.
 2. 관측이 **선택을 바꾸지 않는가** — 관측을 넣기 전과 후의 selector 결과가
    같아야 한다. 관측은 부수 효과여야 하고 결정에 개입하면 안 된다.

모델을 올리지 않는 구간만 다룬다 (test_pose.py와 같은 규약).
"""

from __future__ import annotations

import inspect
import json

import pytest

from supersub_agent import observability as obs
from supersub_agent.pose import (
    COCO_PERSON_LABEL,
    PERSON_ELIGIBLE_THRESHOLD,
    PoseResult,
    _count_person_candidates,
    _largest_person_box,
)


def dets(*people, other=()):
    """(score, x1, y1, x2, y2) 목록으로 검출 결과를 만든다.

    other는 person이 아닌 클래스 — 후보에 섞이면 안 된다.
    """
    scores = [p[0] for p in people] + [o[0] for o in other]
    labels = [COCO_PERSON_LABEL] * len(people) + [o[1] for o in other]
    boxes = [list(p[1:]) for p in people] + [list(o[2:]) for o in other]
    return {"scores": scores, "labels": labels, "boxes": boxes}


# ─────────────────────────────────────────────── A. candidate counting

@pytest.mark.parametrize(
    "people, expected",
    [
        ([], (0, 0)),
        ([(0.9, 0, 0, 10, 10)], (1, 1)),
        ([(0.9, 0, 0, 10, 10), (0.7, 20, 0, 30, 10)], (2, 2)),
        ([(0.9, 0, 0, 10, 10), (0.7, 20, 0, 30, 10), (0.6, 40, 0, 50, 10)], (3, 3)),
        ([(0.9, 0, 0, 10, 10)] * 5, (5, 5)),
    ],
)
def test_counts_people_per_frame(people, expected):
    assert _count_person_candidates(dets(*people)) == expected


def test_low_score_people_are_raw_but_not_eligible():
    """점수가 낮은 사람은 raw에는 들어가고 eligible에서는 빠진다.

    selector가 보지 않는 후보를 다중인원으로 세면 노출이 과대평가된다.
    """
    d = dets((0.9, 0, 0, 10, 10), (0.31, 20, 0, 30, 10))
    assert _count_person_candidates(d) == (2, 1)


def test_non_person_labels_are_not_candidates():
    d = dets((0.9, 0, 0, 10, 10), other=[(0.99, 32, 5, 5, 9, 9)])  # sports_ball
    assert _count_person_candidates(d) == (1, 1)


def test_eligible_threshold_matches_the_selector():
    """관측 임계값이 selector의 기본값과 같아야 한다.

    둘이 갈라지면 기록이 selector의 실제 후보 집합을 설명하지 못한다.
    선택 로직을 바꾸지 않고 이 일치만 지킨다.
    """
    default = inspect.signature(_largest_person_box).parameters["threshold"].default
    assert PERSON_ELIGIBLE_THRESHOLD == default


# ─────────────────────────────────────────── B. selector regression

@pytest.mark.parametrize(
    "people",
    [
        [(0.9, 0, 0, 10, 10)],
        [(0.9, 0, 0, 10, 10), (0.8, 0, 0, 40, 40)],           # 두 번째가 더 큼
        [(0.6, 0, 0, 100, 100), (0.99, 0, 0, 5, 5)],          # 점수 낮아도 크면 선택
        [(0.4, 0, 0, 100, 100), (0.8, 0, 0, 10, 10)],         # 임계값 미만은 제외
        [],
    ],
)
def test_counting_does_not_change_the_selection(people):
    """관측 전/후로 선택 결과가 같다 — 관측은 선택의 부수 효과가 아니다."""
    d = dets(*people)
    before = _largest_person_box(d)

    _count_person_candidates(d)          # 관측 ON

    after = _largest_person_box(d)
    assert before == after


def test_counting_does_not_mutate_detections():
    d = dets((0.9, 0, 0, 10, 10), (0.7, 20, 0, 30, 10))
    snapshot = json.dumps(d, sort_keys=True)
    _count_person_candidates(d)
    assert json.dumps(d, sort_keys=True) == snapshot


# ─────────────────────────────────────────── C. metric aggregation

def test_summary_matches_the_worked_example():
    """[1, 1, 2, 3, 1] → 1인 3프레임, 2인 이상 2프레임, 비율 0.4."""
    s = obs.summarize_candidate_counts([1, 1, 2, 3, 1])
    assert s["analyzed_frame_count"] == 5
    assert s["frames_with_1_person"] == 3
    assert s["frames_with_ge2_person"] == 2
    assert s["multi_person_frame_ratio"] == pytest.approx(0.4)


def test_zero_person_frames_stay_in_the_denominator():
    """사람이 안 잡힌 프레임을 분모에서 빼면 다중인원 노출이 부풀려진다."""
    s = obs.summarize_candidate_counts([0, 0, 2, 2])
    assert s["frames_with_0_person"] == 2
    assert s["frames_with_ge2_person"] == 2
    assert s["multi_person_frame_ratio"] == pytest.approx(0.5)


def test_histogram_buckets_the_long_tail():
    s = obs.summarize_candidate_counts([0, 1, 2, 3, 9])
    assert s["candidate_count_histogram"] == {"0": 1, "1": 1, "2": 1, "3": 1, "6+": 1}
    assert s["max_candidate_count"] == 9      # 상한은 표시용일 뿐 집계는 원본으로
    assert s["frames_with_3plus_person"] == 2


def test_empty_clip_does_not_divide_by_zero():
    s = obs.summarize_candidate_counts([])
    assert s["analyzed_frame_count"] == 0
    assert s["multi_person_frame_ratio"] == 0.0


# ─────────────────────────────────────────── D. FPS metadata

def test_record_keeps_the_actual_fps_values():
    """목표 fps가 아니라 실제 입력에서 얻은 값을 남긴다."""
    rec = obs.build_record(
        source_fps=25.0, sampled_fps=12.5, eligible_counts=[1, 2], rubric_key="a/b")
    assert rec["source_fps"] == 25.0
    assert rec["sampled_fps"] == 12.5
    assert rec["rubric_key"] == "a/b"
    assert rec["analysis_id"] and rec["analyzed_at"]


def test_raw_counts_are_recorded_separately():
    rec = obs.build_record(
        source_fps=30, sampled_fps=15,
        eligible_counts=[1, 1], raw_counts=[1, 3])
    assert rec["frames_with_ge2_person"] == 0        # selector 기준
    assert rec["raw_frames_with_ge2_person"] == 1    # 검출기 기준
    assert rec["raw_multi_person_frame_ratio"] == pytest.approx(0.5)


# ─────────────────────────────────────────── E. persistence

def test_records_round_trip_through_the_sink(tmp_path):
    sink = tmp_path / "m.jsonl"
    a = obs.build_record(source_fps=30, sampled_fps=15, eligible_counts=[1, 2])
    b = obs.build_record(source_fps=60, sampled_fps=15, eligible_counts=[0, 0, 3])
    obs.record(a, sink)
    obs.record(b, sink)

    got = obs.load(sink)
    assert [r["analysis_id"] for r in got] == [a["analysis_id"], b["analysis_id"]]


def test_sink_failure_does_not_raise(tmp_path):
    """관측이 실패해도 분석을 깨뜨리지 않는다."""
    blocked = tmp_path / "file.txt"
    blocked.write_text("not a directory")
    assert obs.record({"x": 1}, blocked / "nested" / "m.jsonl") is None


def test_load_skips_a_truncated_line(tmp_path):
    sink = tmp_path / "m.jsonl"
    sink.write_text('{"analysis_id": "ok"}\n{"analysis_id": "trunc"\n')
    assert [r["analysis_id"] for r in obs.load(sink)] == ["ok"]


def test_aggregate_separates_clip_and_frame_units(tmp_path):
    recs = [
        obs.build_record(source_fps=30, sampled_fps=15, eligible_counts=[1, 1, 1, 1]),
        obs.build_record(source_fps=60, sampled_fps=15, eligible_counts=[2, 2]),
    ]
    agg = obs.aggregate(recs)
    assert agg["total_clips"] == 2
    assert agg["total_analyzed_frames"] == 6
    assert agg["frames_with_ge2_person"] == 2
    assert agg["multi_person_frame_ratio"] == pytest.approx(2 / 6)
    assert agg["clips_with_any_multi_person"] == 1     # 클립 단위는 따로 센다
    assert agg["median_sampled_fps"] == 15


def test_aggregate_of_nothing_is_empty_not_an_error():
    assert obs.aggregate([])["total_clips"] == 0


# ────────────────────────────────── F. backward compatibility

def test_pose_result_still_constructs_without_candidate_counts():
    """이 필드를 모르는 기존 호출부가 그대로 동작한다."""
    import numpy as np
    r = PoseResult(
        keypoints=np.zeros((3, 17, 3)), frames=[], source_fps=30, sampled_fps=15)
    assert r.candidate_counts == []
    assert r.eligible_candidate_counts() == []
    assert r.frame_to_seconds(15) == pytest.approx(1.0)   # 기존 동작 유지


def test_pose_result_exposes_both_count_views():
    import numpy as np
    r = PoseResult(
        keypoints=np.zeros((2, 17, 3)), frames=[], source_fps=30, sampled_fps=15,
        candidate_counts=[(3, 1), (2, 2)])
    assert r.raw_candidate_counts() == [3, 2]
    assert r.eligible_candidate_counts() == [1, 2]


# ───────────────────────────── 배선(wiring) — 파이프라인이 기록을 보장하는가
#
# 관측이 HTTP 핸들러가 아니라 extract_keypoints 안에서 일어나야 한다. 그래야
# 새 호출자(job worker 등)가 배선을 잊어도 기록이 빠지지 않는다.
# 모델·GPU 없이 검사하려고 검출기/포즈 모델을 stub으로 갈아 끼운다.

import numpy as np  # noqa: E402

from supersub_agent import pose as pose_mod  # noqa: E402


def _write_clip(path, n_frames=4, fps=30.0, size=(64, 48)):
    import cv2
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    if not w.isOpened():
        pytest.skip("MJPG 인코더를 쓸 수 없는 환경")
    for i in range(n_frames):
        w.write(np.full((size[1], size[0], 3), i % 256, dtype=np.uint8))
    w.release()
    return str(path)


class _Batch(dict):
    def to(self, _device):
        return self


class _StubDetProcessor:
    """RT-DETR 전처리기 대역. 프레임마다 사람 2명을 낸다."""

    def __call__(self, images=None, return_tensors=None, **kw):
        return _Batch()

    def post_process_object_detection(self, outputs, target_sizes=None, threshold=0.3):
        return [{
            "scores": [0.95, 0.80],
            "labels": [pose_mod.COCO_PERSON_LABEL, pose_mod.COCO_PERSON_LABEL],
            "boxes": [[0, 0, 30, 40], [30, 0, 40, 20]],
        }]


class _StubPoseProcessor:
    def __call__(self, image=None, boxes=None, return_tensors=None, **kw):
        return _Batch()

    def post_process_pose_estimation(self, outputs, boxes=None):
        return [[{"keypoints": np.zeros((17, 2)), "scores": np.full(17, 0.9)}]]


class _StubModel:
    def to(self, _device):
        return self

    def eval(self):
        return self

    def __call__(self, **kw):
        return object()


@pytest.fixture
def stub_models(monkeypatch):
    import transformers
    monkeypatch.setattr(
        transformers.AutoProcessor, "from_pretrained",
        classmethod(lambda cls, name, *a, **k: (
            _StubDetProcessor() if name == pose_mod.PERSON_DETECTOR
            else _StubPoseProcessor())))
    monkeypatch.setattr(
        transformers.RTDetrForObjectDetection, "from_pretrained",
        classmethod(lambda cls, *a, **k: _StubModel()))
    monkeypatch.setattr(
        transformers.VitPoseForPoseEstimation, "from_pretrained",
        classmethod(lambda cls, *a, **k: _StubModel()))


def test_observe_defaults_to_true():
    """기본값이 True여야 새 호출자가 자동으로 관측에 포함된다 (fail-safe)."""
    default = inspect.signature(
        pose_mod.extract_keypoints).parameters["observe"].default
    assert default is True


def test_pipeline_records_exactly_once(tmp_path, monkeypatch, stub_models):
    """extract_keypoints 한 번 = 레코드 한 줄. 진입점이 아니라 여기서 보장된다."""
    sink = tmp_path / "m.jsonl"
    monkeypatch.setenv("SUPERSUB_METRICS_SINK", str(sink))

    clip = _write_clip(tmp_path / "c.avi", n_frames=4, fps=30.0)
    result = pose_mod.extract_keypoints(clip, device="cpu", rubric_key="football/instep_shot")

    recs = obs.load(sink)
    assert len(recs) == 1
    r = recs[0]
    assert r["rubric_key"] == "football/instep_shot"
    assert r["analyzed_frame_count"] == len(result.keypoints)
    # stub이 프레임마다 사람 2명을 내므로 전 프레임이 다중인원이다.
    assert r["frames_with_ge2_person"] == r["analyzed_frame_count"]
    assert r["multi_person_frame_ratio"] == pytest.approx(1.0)
    assert r["source_fps"] > 0 and r["sampled_fps"] > 0


def test_observe_false_records_nothing(tmp_path, monkeypatch, stub_models):
    """CLI·오프라인 경로는 서비스 입력 분포를 오염시키지 않는다."""
    sink = tmp_path / "m.jsonl"
    monkeypatch.setenv("SUPERSUB_METRICS_SINK", str(sink))

    clip = _write_clip(tmp_path / "c.avi")
    pose_mod.extract_keypoints(clip, device="cpu", observe=False)

    assert obs.load(sink) == []
    assert not sink.exists()


def test_api_video_does_not_record_a_second_time():
    """api.py는 직접 기록하지 않는다 — 하면 한 분석이 두 번 남는다."""
    from supersub_agent import api
    src = inspect.getsource(api.api_video)
    assert "observability.record" not in src
    assert "build_record" not in src
    # 관측 라벨은 extract_keypoints로 넘긴다.
    assert "rubric_key=rubric" in src


def test_synthetic_endpoint_is_not_service_input():
    """합성 키포인트에는 영상도 후보도 없다. 서비스 입력으로 분류하지 않는다."""
    from supersub_agent import api
    src = inspect.getsource(api.api_synthetic)
    assert "extract_keypoints" not in src
    assert "observability" not in src


def test_cli_scripts_opt_out_explicitly():
    """CLI가 관측에서 빠지는 것은 명시적이어야 한다 — 조용히 빠지면 안 된다."""
    from pathlib import Path as _P
    root = _P(__file__).resolve().parent.parent / "scripts"
    for name in ("analyze.py", "measure.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "extract_keypoints(" in src
        assert "observe=False" in src, f"{name}에 observe=False가 없다"


def test_offline_evaluation_opts_out_explicitly():
    """Phase A 오프라인 추출이 서비스 입력 sink를 오염시키지 않아야 한다.

    이 스크립트는 39클립을 한 번에 돌린다. observe 기본값(True)에 걸리면 한 번의
    재실행으로 서비스 입력 분포가 통째로 뒤집힌다 — 실제 서비스 레코드가 0건인
    지금은 39건이 전부 서비스 입력으로 보이게 된다.
    """
    from pathlib import Path as _P
    src = (_P(__file__).resolve().parent.parent / "eval" / "phaseA" / "extract.py"
           ).read_text(encoding="utf-8")
    assert "extract_keypoints(" in src
    assert "observe=False" in src, "eval/phaseA/extract.py에 observe=False가 없다"


def test_production_pose_result_always_has_candidate_counts(
        tmp_path, monkeypatch, stub_models):
    """production 생성 경로에서 candidate_counts가 비는 일이 없어야 한다."""
    monkeypatch.setenv("SUPERSUB_METRICS_SINK", str(tmp_path / "m.jsonl"))
    clip = _write_clip(tmp_path / "c.avi", n_frames=5)
    result = pose_mod.extract_keypoints(clip, device="cpu")

    assert len(result.candidate_counts) == len(result.keypoints)
    assert all(e == 2 for e in result.eligible_candidate_counts())


def test_sink_failure_does_not_break_extraction(tmp_path, monkeypatch, stub_models):
    """sink가 고장나도 분석은 끝난다 — 관측은 부수 효과다."""
    blocked = tmp_path / "file.txt"
    blocked.write_text("not a directory")
    monkeypatch.setenv("SUPERSUB_METRICS_SINK", str(blocked / "nested" / "m.jsonl"))

    clip = _write_clip(tmp_path / "c.avi")
    result = pose_mod.extract_keypoints(clip, device="cpu")   # 예외가 나면 안 된다
    assert len(result.keypoints) > 0


def test_sink_failure_warns_once(tmp_path, caplog):
    """기록 실패를 조용히 넘기지 않는다 — 0건과 고장을 구분할 수 있어야 한다."""
    monkeypatch_flag = obs._WARNED_ONCE
    obs._WARNED_ONCE = False
    try:
        blocked = tmp_path / "f.txt"
        blocked.write_text("x")
        bad = blocked / "nested" / "m.jsonl"
        with caplog.at_level("WARNING"):
            assert obs.record({"a": 1}, bad) is None
            assert obs.record({"a": 2}, bad) is None
        assert len(caplog.records) == 1      # 분석마다 같은 줄을 쌓지 않는다
    finally:
        obs._WARNED_ONCE = monkeypatch_flag


def test_serialization_error_is_not_swallowed():
    """직렬화 오류는 운영 문제가 아니라 프로그래밍 오류다. 조용히 넘기지 않는다."""
    with pytest.raises(TypeError):
        obs.record({"bad": object()}, "/dev/null")
