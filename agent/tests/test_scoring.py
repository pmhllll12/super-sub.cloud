"""점수 합산 로직 검증.

핵심 성질: 같은 판정 입력은 언제나 같은 점수를 낸다(결정론).
"""

from __future__ import annotations

import pytest

from supersub_agent.scoring import (
    RubricError,
    aggregate,
    discover_rubrics,
    load_rubric,
)

RUBRIC_PATH = "rubrics/football_instep_shot.yaml"


@pytest.fixture(scope="module")
def rubric():
    return load_rubric(RUBRIC_PATH)


def test_rubric_loads_and_weights_sum_to_one(rubric):
    assert rubric.sport == "football"
    assert rubric.motion == "instep_shot"
    assert abs(sum(c.weight for c in rubric.criteria) - 1.0) < 1e-6
    assert len(rubric.criteria) == 6


def test_discover_rubrics_keys_by_sport_and_motion():
    """루브릭 추가가 코드 변경이 아니라 파일 추가로 끝나는지."""
    found = discover_rubrics("rubrics")

    assert "football/instep_shot" in found
    for key, r in found.items():
        assert key == f"{r.sport}/{r.motion}", "키는 파일명이 아니라 내용에서 온다"


def test_every_rubric_loads_and_is_wellformed():
    """rubrics/의 모든 파일이 적재 규칙(가중치 합·bands·앵커)을 지키는지.

    새 루브릭을 넣었을 때 여기서 걸린다.
    """
    for key, r in discover_rubrics("rubrics").items():
        assert abs(sum(c.weight for c in r.criteria) - 1.0) < 1e-6, key
        for c in r.criteria:
            assert c.band_metric in c.measured_by, f"{key}/{c.id}"
            assert {a["grade"] for a in c.anchors} == {0, 1, 2}, f"{key}/{c.id}"
            assert set(c.titles) == {0, 1, 2}, f"{key}/{c.id}: 칭호 누락"


def test_duplicate_rubric_key_is_rejected(tmp_path):
    """같은 (종목, 동작)이 두 파일에 있으면 어느 쪽이 쓰일지 모호하다."""
    body = ("sport: x\nmotion: y\ncriteria:\n"
            "  - {id: a, name: A, weight: 1.0, measured_by: [m], "
            "grades: {0: z, 1: z, 2: z}, " + _BANDS + "}\n")
    (tmp_path / "one.yaml").write_text(body, encoding="utf-8")
    (tmp_path / "two.yaml").write_text(body, encoding="utf-8")

    with pytest.raises(RubricError, match="키 중복"):
        discover_rubrics(tmp_path)


def test_rubric_is_flagged_provisional(rubric):
    """지도자 검수 전이므로 provisional 플래그가 서야 한다."""
    assert rubric.review_required is True


def test_open_scope_is_one_motion_per_sport():
    """지금 여는 범위는 종목당 한 동작이다.

    동작을 하나 여는 비용은 YAML 작성이 아니라 임계값 실측·지도자 검수·검증
    클립이다. 열린 동작이 늘면 검수 대상이 함께 늘어야 하므로, 늘리는 순간
    여기서 걸리게 둔다.
    """
    active = {k for k, r in discover_rubrics("rubrics").items() if r.is_active}

    assert active == {
        "football/instep_shot",
        "baseball/pitching",
        "basketball/jump_shot",
    }
    sports = [k.split("/")[0] for k in active]
    assert len(sports) == len(set(sports)), "한 종목에 두 동작이 열려 있다"


def test_closed_motions_stay_loadable():
    """닫아 둔 동작도 적재는 된다 — 검수·실측을 UI와 무관하게 돌리기 위해서다.

    계약 테스트(test_pipeline_covers_every_rubric_metric)도 이 파일들을 계속
    돌므로, 닫혀 있는 동안 파이프라인이 바뀌어 지표가 어긋나면 여는 시점이
    아니라 그때 걸린다.
    """
    closed = {k: r for k, r in discover_rubrics("rubrics").items() if not r.is_active}

    assert set(closed) == {"football/inside_pass", "basketball/layup"}
    for key, r in closed.items():
        assert r.criteria, key
        assert r.status == "draft", key


def test_unknown_status_is_rejected(tmp_path):
    """오타로 조용히 닫히면 안 된다 — 열려야 할 동작이 사라지는 쪽이 못 찾는다."""
    (tmp_path / "one.yaml").write_text(
        "sport: x\nmotion: y\nstatus: enabled\ncriteria:\n"
        "  - {id: a, name: A, weight: 1.0, measured_by: [m], "
        "grades: {0: z, 1: z, 2: z}, " + _BANDS + "}\n",
        encoding="utf-8",
    )

    with pytest.raises(RubricError, match="status"):
        discover_rubrics(tmp_path)


def test_status_defaults_to_active(tmp_path):
    """status를 안 쓴 옛 루브릭은 그대로 열린 것으로 본다."""
    (tmp_path / "one.yaml").write_text(
        "sport: x\nmotion: y\ncriteria:\n"
        "  - {id: a, name: A, weight: 1.0, measured_by: [m], "
        "grades: {0: z, 1: z, 2: z}, " + _BANDS + "}\n",
        encoding="utf-8",
    )

    assert discover_rubrics(tmp_path)["x/y"].is_active


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

    n = len(rubric.criteria)
    heavy, rest = 0.30, 0.70 / (n - 1)
    reweighted = rubric.__class__(
        sport=rubric.sport,
        motion=rubric.motion,
        version=rubric.version,
        criteria=tuple(
            c.__class__(**{**c.__dict__, "weight": heavy if c.id == "hip_rotation" else rest})
            for c in rubric.criteria
        ),
        grade_bands=rubric.grade_bands,
        review_required=rubric.review_required,
        pipeline_version=rubric.pipeline_version,
    )
    assert aggregate(judgments, reweighted)["score"] == 70


def test_missing_judgment_is_rejected_when_expected(rubric):
    """판정이 실패해 빠진 항목은 오류다 — 조용히 제외되면 점수가 왜곡된다."""
    judgments = _judgments(2, rubric)
    del judgments["trunk_lean"]
    with pytest.raises(ValueError, match="누락"):
        aggregate(judgments, rubric, expected_ids=rubric.criterion_ids)


def test_skipped_criterion_renormalizes_weights(rubric):
    """도구 미검출로 빠진 항목은 0점이 아니라 제외다.

    빠진 항목을 0점으로 두면 촬영 조건 때문에 선수가 감점된다.
    남은 항목이 모두 2등급이면 총점은 100점이어야 한다.
    """
    judgments = _judgments(2, rubric)
    del judgments["plant_foot_position"]

    result = aggregate(judgments, rubric)

    assert result["score"] == 100
    assert [s["criterion_id"] for s in result["skipped"]] == ["plant_foot_position"]
    # breakdown의 weight는 표시용 4자리 반올림이라 합이 정확히 1.0은 아니다.
    # 점수는 반올림 전 값으로 계산되므로 score == 100이 실제 검증이다.
    assert sum(b["weight"] for b in result["breakdown"]) == pytest.approx(1.0, abs=1e-3)


def test_unknown_criterion_is_rejected(rubric):
    judgments = _judgments(2, rubric)
    judgments["없는항목"] = {"grade": 2, "evidence": "", "metric_ref": ""}
    with pytest.raises(ValueError, match="루브릭에 없는"):
        aggregate(judgments, rubric)


def test_applicable_criteria_drops_tool_dependent_items(rubric):
    """공이 없는 측정값에서는 도구 기반 항목이 빠진다."""
    pose_only = {
        "plant_knee_angle_at_impact": 160.0,
        "swing_knee_angle_at_impact": 150.0,
        "trunk_forward_lean_deg_at_impact": 10.0,
        "hip_rotation_range_deg": 30.0,
        "swing_hip_flexion_after_impact_deg": 35.0,
        "follow_through_duration_frames": 8,
    }

    ids = [c.id for c in rubric.applicable_criteria(pose_only)]
    assert "plant_foot_position" not in ids
    assert len(ids) == len(rubric.criteria) - 1

    with_ball = {**pose_only, "plant_foot_to_ball_offset": 0.29}
    assert len(rubric.applicable_criteria(with_ball)) == len(rubric.criteria)


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
