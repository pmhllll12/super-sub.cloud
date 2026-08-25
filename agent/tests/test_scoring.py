"""점수 합산 로직 검증.

핵심 성질: 같은 판정 입력은 언제나 같은 점수를 낸다(결정론).
"""

from __future__ import annotations

import pytest

from supersub_agent.scoring import RubricError, aggregate, load_rubric

RUBRIC_PATH = "rubrics/football_instep_shot.yaml"


@pytest.fixture(scope="module")
def rubric():
    return load_rubric(RUBRIC_PATH)


def test_rubric_loads_and_weights_sum_to_one(rubric):
    assert rubric.sport == "football"
    assert rubric.motion == "instep_shot"
    assert abs(sum(c.weight for c in rubric.criteria) - 1.0) < 1e-6
    assert len(rubric.criteria) == 5


def test_rubric_is_flagged_provisional(rubric):
    """지도자 검수 전이므로 provisional 플래그가 서야 한다."""
    assert rubric.review_required is True


def test_every_criterion_has_measurable_basis(rubric):
    """근거 지표가 없는 항목은 판정할 수 없다."""
    for c in rubric.criteria:
        assert c.measured_by, f"{c.id}에 measured_by가 없음"


def test_every_criterion_has_anchors(rubric):
    """소형 모델에서는 등급별 앵커 예시가 필수다."""
    for c in rubric.criteria:
        assert len(c.anchors) >= 3, f"{c.id}의 앵커가 3개 미만"
        assert {a["grade"] for a in c.anchors} == {0, 1, 2}


def _judgments(grade: int, rubric) -> dict:
    return {
        c.id: {"grade": grade, "evidence": "테스트", "metric_ref": c.measured_by[0]}
        for c in rubric.criteria
    }


def test_all_top_grades_score_100(rubric):
    result = aggregate(_judgments(2, rubric), rubric)
    assert result["score"] == 100
    assert result["grade"] == "A"


def test_all_zero_grades_score_0(rubric):
    result = aggregate(_judgments(0, rubric), rubric)
    assert result["score"] == 0
    assert result["grade"] == "D"


def test_all_mid_grades_score_50(rubric):
    result = aggregate(_judgments(1, rubric), rubric)
    assert result["score"] == 50
    assert result["grade"] == "C"


def test_scoring_is_deterministic(rubric):
    """동일 판정을 20회 합산해도 점수가 흔들리지 않아야 한다."""
    judgments = {
        "plant_knee_flexion": {"grade": 2, "evidence": "", "metric_ref": ""},
        "swing_knee_extension": {"grade": 1, "evidence": "", "metric_ref": ""},
        "trunk_lean": {"grade": 2, "evidence": "", "metric_ref": ""},
        "hip_rotation": {"grade": 0, "evidence": "", "metric_ref": ""},
        "follow_through": {"grade": 1, "evidence": "", "metric_ref": ""},
    }
    scores = {aggregate(judgments, rubric)["score"] for _ in range(20)}
    assert len(scores) == 1


def test_weight_change_recomputes_without_reanalysis(rubric):
    """가중치를 바꾸면 같은 판정에서 다른 점수가 나와야 한다 —
    재분석 없이 재계산된다는 설계 주장을 검증한다."""
    judgments = _judgments(2, rubric)
    judgments["hip_rotation"]["grade"] = 0

    baseline = aggregate(judgments, rubric)["score"]
    assert baseline == 85  # hip_rotation 가중치 0.15만 손실

    reweighted = rubric.__class__(
        sport=rubric.sport,
        motion=rubric.motion,
        version=rubric.version,
        criteria=tuple(
            c.__class__(**{**c.__dict__, "weight": 0.30 if c.id == "hip_rotation" else 0.175})
            for c in rubric.criteria
        ),
        grade_bands=rubric.grade_bands,
        review_required=rubric.review_required,
        pipeline_version=rubric.pipeline_version,
    )
    assert aggregate(judgments, reweighted)["score"] == 70


def test_missing_judgment_is_rejected(rubric):
    judgments = _judgments(2, rubric)
    del judgments["trunk_lean"]
    with pytest.raises(ValueError, match="누락"):
        aggregate(judgments, rubric)


def test_out_of_range_grade_is_rejected(rubric):
    """연속 점수가 흘러들어오는 것을 막는다."""
    judgments = _judgments(2, rubric)
    judgments["trunk_lean"]["grade"] = 87
    with pytest.raises(ValueError, match="0/1/2"):
        aggregate(judgments, rubric)


_BANDS = "bands: {metric: m, 2: [[2, null]], 1: [[1, 2]], 0: [[null, 1]]}"


def _minimal_rubric(tmp_path, *, weight=0.5, bands=_BANDS):
    path = tmp_path / "r.yaml"
    path.write_text(
        "sport: x\nmotion: y\ncriteria:\n"
        f"  - {{id: a, name: A, weight: {weight}, measured_by: [m], "
        f"grades: {{0: z, 1: z, 2: z}}, {bands}}}\n",
        encoding="utf-8",
    )
    return path


def test_bad_weights_are_rejected(tmp_path):
    with pytest.raises(RubricError, match="가중치 합"):
        load_rubric(_minimal_rubric(tmp_path))


def test_bands_are_required(tmp_path):
    """등급을 코드가 판정하므로 bands 없는 항목은 적재 단계에서 막는다."""
    with pytest.raises(RubricError, match="bands 없음"):
        load_rubric(_minimal_rubric(tmp_path, weight=1.0, bands="anchors: []"))


def test_band_metric_must_be_measured(tmp_path):
    """measured_by에 없는 지표로 등급을 정할 수 없다."""
    bands = "bands: {metric: other, 2: [[2, null]], 1: [[1, 2]], 0: [[null, 1]]}"
    with pytest.raises(RubricError, match="measured_by에 없음"):
        load_rubric(_minimal_rubric(tmp_path, weight=1.0, bands=bands))


def test_grade_for_uses_intervals_not_the_model(rubric):
    """등급은 수치 구간으로 결정된다 — 경계값 포함.

    EXAONE 1.2B가 141.7을 140~165 밖이라고 재현되게 틀린 것이 이 판정을
    코드로 내린 이유다.
    """
    swing = next(c for c in rubric.criteria if c.id == "swing_knee_extension")
    assert swing.band_metric == "swing_knee_angle_at_impact"

    cases = [(141.7, 2), (140.0, 2), (139.2, 0), (165.0, 2), (175.0, 1), (179.2, 0)]
    for value, expected in cases:
        assert swing.grade_for({swing.band_metric: value}) == expected, value


def test_grade_for_rejects_uncovered_value(tmp_path):
    """구간이 값을 덮지 못하면 조용히 등급을 매기지 않고 오류를 낸다."""
    bands = "bands: {metric: m, 2: [[2, 3]], 1: [[1, 2]], 0: [[0, 1]]}"
    r = load_rubric(_minimal_rubric(tmp_path, weight=1.0, bands=bands))
    c = r.criteria[0]

    assert c.grade_for({"m": 2.5}) == 2
    with pytest.raises(RubricError, match="어느 등급 구간에도 없음"):
        c.grade_for({"m": 10.0})
