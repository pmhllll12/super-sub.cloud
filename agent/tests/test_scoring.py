"""점수 합산 로직 검증.

핵심 성질: 같은 판정 입력은 언제나 같은 점수를 낸다(결정론).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from supersub_agent.scoring import (
    SCORE_BANDS,
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

    assert active == {"football/instep_shot"}
    sports = [k.split("/")[0] for k in active]
    assert len(sports) == len(set(sports)), "한 종목에 두 동작이 열려 있다"


def test_closed_motions_stay_loadable():
    """닫아 둔 동작도 적재는 된다 — 검수·실측을 UI와 무관하게 돌리기 위해서다.

    계약 테스트(test_pipeline_covers_every_rubric_metric)도 이 파일들을 계속
    돌므로, 닫혀 있는 동안 파이프라인이 바뀌어 지표가 어긋나면 여는 시점이
    아니라 그때 걸린다.
    """
    closed = {k: r for k, r in discover_rubrics("rubrics").items() if not r.is_active}

    # 2026.09.11 축구 단일 종목 전환 — 야구·농구 루브릭 4개를 지웠다.
    # 🔴 `eval/` 은 남겨 뒀다. 사전등록 실험(7·20·34·37번)이 그 클립
    # 측정치 위에 서 있고, 한 회차가 6종을 **같은 문서에서** 쟀기 때문에
    # 종목으로 잘리지 않는다. 좌우·관절 매핑 검사 자체는 `eval/` 을 읽지
    # 않는다 (`test_keypoint_source` → `scripts/analyze_keypoints.py`).
    assert set(closed) == {"football/inside_pass"}
    for key, r in closed.items():
        assert r.criteria, key
        assert r.status == "draft", key


def test_open_ended_top_bands_are_rejected(tmp_path):
    """상위 등급 구간의 끝이 열려 있으면 적재에서 막는다.

    위가 열린 2등급은 측정 오류를 만점으로 만든다 — 야구 투구 실클립에서 골반
    회전 181.1도(좌우 라벨 스왑으로 부풀려진 값)가 "40도 이상"에 걸려 장점으로
    표시됐다. 0등급만 열어 둔다.
    """
    body = ("sport: x\nmotion: y\ncriteria:\n"
            "  - {id: a, name: A, weight: 1.0, measured_by: [m], "
            "grades: {0: z, 1: z, 2: z}, "
            "bands: {metric: m, 2: [[2, null]], 1: [[1, 2]], 0: [[null, 1]]}}\n")
    (tmp_path / "one.yaml").write_text(body, encoding="utf-8")

    with pytest.raises(RubricError, match="열려 있음"):
        discover_rubrics(tmp_path)


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


# 상위 등급의 열린 끝은 이제 적재에서 막힌다 — 0등급만 열어 둔다.
_BANDS = "bands: {metric: m, 2: [[2, 3]], 1: [[1, 2]], 0: [[null, 1]]}"


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


def test_band_text_states_the_actual_interval(rubric):
    """근거 문장에 들어갈 기준 구간은 코드가 만든다.

    등급 정의만 주면 모델이 없는 상한을 지어낸다 — 실클립에서 "40도 이상"인
    기준이 화면에 "40~165도"로 나갔다. 구간을 문장으로 확정해 넘긴다.
    """
    from supersub_agent.judge import band_text, system_prompt

    c = rubric.get("hip_rotation")
    assert band_text(c, 2) == "25~180"
    assert band_text(c, 1) == "15~25"
    assert band_text(c, 0) == "15 이하"

    assert "축구" in system_prompt("football")
    assert "생활체육" in system_prompt(""), "모르는 종목은 특정하지 않는다"
    assert "생활체육" in system_prompt("baseball"), (
        "루브릭 없는 종목 코드에 이름을 붙이고 있다 — 축구 단일 종목이다"
    )


def test_out_of_band_marks_zero_grades_that_came_from_above():
    """🔴 0등급이 **구간 위에서** 왔으면 표시한다 (미결 20번, 처방 「다」).

    상위 등급의 위를 닫는 규칙은 오측정이 만점이 되는 것을 막는다(투구 골반
    181.1도가 「40도 이상」에 걸려 장점으로 표시된 적이 있다). 그 규칙은 맞다.
    문제는 **닫은 위쪽이 갈 곳이 0등급뿐**이라 「쟀는데 못했다」와 「구간
    밖이다」가 같은 0점이 된다는 것이다 — 실측으로 0등급 117건 중 23건(20%)이
    구간 위에서 왔다.

    지우면 화면이 둘을 다시 구분하지 못한다.
    """
    rubric = load_rubric(RUBRIC_PATH)
    base = {m: 0.0 for cr in rubric.criteria for m in cr.measured_by}

    # 🔴 상한을 **막 넘긴** 값은 대개 1등급으로 간다 — 1등급 구간이 2등급
    # 구간을 감싸기 때문이다. 0등급은 **더 멀리** 넘어야 걸린다. 그래서
    # "상한 초과 = 0등급"으로 단정하지 말고 실제로 0이 되는 자리를 찾는다.
    c = ceiling = above = None
    for cand in rubric.criteria:
        ceil = cand.top_ceiling()
        if ceil is None:
            continue
        for step in (0.5, 5.0, 20.0, 60.0):
            probe = {**base, cand.band_metric: ceil + step}
            try:
                hit = cand.grade_for(probe) == 0
            except RubricError:
                continue  # PLAUSIBLE 밖이라 실제로는 도달하지 않는 값이다
            if hit:
                c, ceiling, above = cand, ceil, probe
                break
        if c is not None:
            break
    assert c is not None, "상한 위가 0등급이 되는 항목이 하나는 있어야 한다"

    below = {**base, c.band_metric: -999.0}
    assert c.grade_for(above) == 0 and c.grade_for(below) == 0, "둘 다 0등급이어야 한다"
    assert c.out_of_band(above) == "above"
    assert c.out_of_band(below) == "", "아래쪽 0등급은 표시하지 않는다"


# features 를 줘야만 채워지는 **표시 전용** 필드들. 이 목록이 늘어날 때마다
# 아래 검사가 「점수를 안 건드린다」를 다시 확인한다.
DISPLAY_ONLY_FIELDS = ("out_of_band", "stat", "view_dependent")


def test_display_only_fields_do_not_move_the_score():
    """🔴 표시는 표시일 뿐이다 — **점수·등급이 바뀌면 B-6 재실행을 부른다.**

    features 를 주든 안 주든 표시 전용 필드를 뺀 나머지가 한 비트도 같아야 한다.
    이 성질 때문에 이 처방들(구간 위 0등급 표시·항목 점수)을 임계값 검수 전에
    넣을 수 있었다.
    """
    rubric = load_rubric(RUBRIC_PATH)
    feats = {m: 0.0 for cr in rubric.criteria for m in cr.measured_by}
    judgments = _judgments(0, rubric)

    without = aggregate(judgments, rubric)
    with_feats = aggregate(judgments, rubric, features=feats)

    strip = lambda r: {  # noqa: E731
        **r, "breakdown": [{k: v for k, v in b.items()
                            if k not in DISPLAY_ONLY_FIELDS}
                           for b in r["breakdown"]]
    }
    assert strip(without) == strip(with_feats)
    assert all(b["out_of_band"] == "" for b in without["breakdown"]), (
        "features 를 안 주면 표시가 없어야 한다"
    )
    assert all(b["stat"] is None for b in without["breakdown"]), (
        "features 를 안 주면 항목 점수를 **지어내지 않는다**"
    )
    assert all(b["view_dependent"] == "" for b in without["breakdown"]), (
        "features 를 안 주면 촬영 방향 의존 표시가 없어야 한다"
    )


def test_item_score_never_contradicts_the_grade():
    """🔴 레이더 차트가 리포트와 반대로 말하면 안 된다.

    항목 점수(`score_for`)는 등급별로 겹치지 않는 자리에 놓인다 —
    2등급 85~100 · 1등급 50~85 · 0등급 0~50. 이 성질이 깨지면 **2등급 항목이
    1등급 항목보다 안쪽에 찍히는** 오각형이 나오고, 선수는 잘한 항목을
    못한 것으로 읽는다.

    루브릭 전체·값 범위 전체를 훑는다. 새 루브릭의 bands 에 빈틈이 생겨도
    여기서 걸린다.
    """
    for key, rubric in discover_rubrics("rubrics").items():
        for c in rubric.criteria:
            ends = [e for iv in sum(c.bands.values(), ()) for e in iv if e is not None]
            lo, hi = min(ends), max(ends)
            span = (hi - lo) or 1.0
            for step in range(-30, 131):
                value = lo + span * step / 100.0
                features = {c.band_metric: value}
                try:
                    grade = c.grade_for(features)
                except RubricError:
                    continue  # bands 가 덮지 않는 값 — 실제로는 도달하지 않는다
                score = c.score_for(features)
                floor, ceiling = SCORE_BANDS[grade]
                assert floor <= score <= ceiling, (
                    f"{key}/{c.id}: {c.band_metric}={value:g} 는 {grade}등급인데 "
                    f"점수 {score} 가 {floor}~{ceiling} 밖이다"
                )


def test_an_open_top_band_is_not_penalised_for_being_far_from_the_middle():
    """🔴 **위가 열린 이상 구간의 끝은 위험한 끝이 아니다.**

    `hip_rotation` 의 2등급은 25~180도이고 180도 위에는 아무 등급도 없다.
    「구간 한가운데가 최고점」으로 재면 골반을 끝까지 돌린 175도가 한가운데
    102도보다 낮게 찍힌다 — **잘한 값을 깎는다.** `_risk_edges` 가 아래쪽
    끝(25도)만 세는 이유다.
    """
    rubric = load_rubric(RUBRIC_PATH)
    c = rubric.get("hip_rotation")
    assert c.bands[2] == ((25.0, 180.0),), "이 검사가 전제하는 구간이 바뀌었다"

    far = c.score_for({c.band_metric: 175.0})
    middle = c.score_for({c.band_metric: 102.0})
    edge = c.score_for({c.band_metric: 27.0})

    assert far > middle > edge, (
        "위험한 끝(25도)에서 멀어질수록 높아야 한다 — 한가운데를 최고점으로 잡으면 "
        f"175도({far})가 102도({middle})보다 낮아진다"
    )
    assert far >= 99.0, "반대쪽 끝은 만점 언저리다"
    assert edge <= 86.0, "위험한 끝에 붙은 값은 2등급 바닥이다"


def test_item_score_is_absent_when_the_metric_was_not_measured():
    """도구 미검출로 빠진 항목은 축이 0이 아니라 **없는** 것이다.

    0으로 채우면 레이더에서 「그 항목을 못했다」로 보인다. 촬영 조건 때문에
    선수가 깎이지 않게 하는 것은 `aggregate` 의 재정규화와 같은 취지다.
    """
    rubric = load_rubric(RUBRIC_PATH)
    c = rubric.criteria[0]
    assert c.score_for({}) is None


# -- 동작(motion) 어휘 — 백엔드가 FK 로 쓸 값이다 (미결 `jin` 17번) -----------


def test_the_motion_vocabulary_is_the_pair_not_the_bare_motion():
    """🔴 동작 코드의 열쇠는 **(종목, 동작) 쌍**이지 `motion` 하나가 아니다.

    지금은 `motion` 값 6개가 전역에서 겹치지 않지만 그것은 **우연이지 보장이
    아니다.** `shot`·`serve` 처럼 여러 종목에 자연스럽게 들어갈 이름이 있고,
    백엔드가 `motion` 만으로 참조 테이블을 만들면(미결 `jin` 17번 B안) 겹치는
    순간 **한 행이 두 루브릭을 가리킨다** — 그러면 농구 영상이 축구 루브릭으로
    채점되고 그 사실이 값에 안 남는다.

    이 검사는 겹침을 금지하지 않는다. **겹치는 날 여기서 걸려서** 그때 쌍으로
    갈지 이름을 바꿀지 정하게 하는 것이 목적이다.
    """
    found = discover_rubrics("rubrics")
    motions = [r.motion for r in found.values()]
    assert len(set(motions)) == len(motions), (
        f"`motion` 이 종목을 넘어 겹친다: {sorted(motions)}. "
        "백엔드 참조 테이블(jin 17번)이 이 값을 단독 키로 쓰고 있으면 함께 고칠 것."
    )
    for key, r in found.items():
        assert key == f"{r.sport}/{r.motion}"


def test_the_filename_matches_the_declared_sport_and_motion():
    """파일명과 선언이 어긋나면 **목록을 파일명으로 세는 사람이 틀린다.**

    미결 `jin` 17번이 "파일명(`baseball_pitching`)은 종목이 섞여 있어
    `sport_code` 와 중복된다"고 적었는데, 그 판단이 서려면 파일명이 실제로
    `<sport>_<motion>` 이어야 한다. 지금은 6개 전부 그렇고 **강제하는 것이
    없었다.**
    """
    expected = {f"{r.sport}_{r.motion}"
                for r in discover_rubrics("rubrics").values()}
    actual = {p.stem for p in Path("rubrics").glob("*.yaml")}
    assert actual == expected, (
        f"파일명이 선언과 다르다: {sorted(actual - expected)}"
    )


def _trunk_criterion(rubric):
    return next(c for c in rubric.criteria
                if c.band_metric == "trunk_forward_lean_deg_at_impact")


@pytest.mark.parametrize(
    "lean, expected",
    [
        # 인스텝의 2등급은 [5,20], 0등급은 ≤0 — 반전하면 2 → 0 이다.
        (12.4, "grade"),
        # 음수도 마찬가지다. -8.7 은 0등급이고 반전하면 8.7 로 2등급이 된다.
        (-8.7, "grade"),
        # 25도는 1등급([20,30])이고 반전한 -25 는 0등급이다.
        (25.0, "grade"),
        # 🔴 33도는 반전해도 0등급이라 **등급이 안 바뀐다** — 그래도 지표가
        # 방향에 의존한다는 것은 그대로다.
        (33.0, "metric"),
    ],
)
def test_view_dependent_says_whether_the_grade_would_have_differed(rubric, lean, expected):
    """🔴 촬영 방향 의존을 **드러낸다** (미결 37번 처방 (다)).

    같은 자세라도 반대편에서 찍으면 `trunk_lean` 이 정확히 `-θ` 가 된다.
    그 사실을 숨기지 않는 것이 이 필드의 전부다.
    """
    assert _trunk_criterion(rubric).view_dependent(
        {"trunk_forward_lean_deg_at_impact": lean}
    ) == expected


def test_view_dependent_is_empty_for_metrics_that_do_not_flip(rubric):
    """무릎각·골반 회전은 좌우 반전에 안 변한다 — 경고를 남발하지 않는다."""
    feats = {m: 30.0 for cr in rubric.criteria for m in cr.measured_by}
    for c in rubric.criteria:
        if c.band_metric == "trunk_forward_lean_deg_at_impact":
            continue
        assert c.view_dependent(feats) == "", f"{c.id} 에 근거 없는 표시가 붙었다"


def test_a_symmetric_band_is_what_actually_stops_the_flip(tmp_path):
    """🔴 **같은 지표, 밴드 하나 차이로 갈린다** (미결 37번의 자기 검사).

    0 대칭 밴드는 좌우가 반전돼도 등급이 안 바뀌고, 비대칭 밴드는 바뀐다.
    인스텝은 실측에서 18/18 이 뒤집혔고, 0 대칭 밴드를 쓰던 루브릭은 46클립
    0/46 이었다 — 같은 지표, 더 큰 부호 분산, 밴드 하나 차이로 0% 대 44%.
    **지표가 아니라 밴드가 결정한다**는 것을 여기에 고정한다.

    🔴 밴드를 **여기서 직접 만든다.** 2026.09.11 축구 단일 종목 전환으로 0
    대칭 밴드를 쓰던 야구 타격 루브릭이 사라졌는데, 그때 이 검사를 함께
    지우면 **대조군이 없어져** "인스텝이 뒤집힌다"만 남는다. 그러면 다음
    사람이 지표를 갈아 치우려 든다 — 고칠 자리는 밴드다.
    """
    text = Path(RUBRIC_PATH).read_text(encoding="utf-8")
    symmetric = text.replace(
        "      2: [[5, 20]]\n"
        "      1: [[0, 5], [20, 30]]\n"
        "      0: [[null, 0], [30, null]]\n",
        "      2: [[-25, 25]]\n"
        "      1: [[-42, -25], [25, 42]]\n"
        "      0: [[null, -42], [42, null]]\n",
    )
    assert symmetric != text, "인스텝의 trunk_lean 밴드 표기가 바뀌었다"
    path = tmp_path / "football_instep_shot.yaml"
    path.write_text(symmetric, encoding="utf-8")

    batting = _trunk_criterion(load_rubric(path))
    instep = _trunk_criterion(load_rubric(RUBRIC_PATH))
    for lean in (-30.0, -12.4, -3.0, 3.0, 12.4, 30.0):
        feats = {"trunk_forward_lean_deg_at_impact": lean}
        assert batting.view_dependent(feats) == "metric", (
            f"대칭 밴드인데 {lean} 에서 등급이 뒤집혔다"
        )
    assert instep.view_dependent(
        {"trunk_forward_lean_deg_at_impact": 12.4}
    ) == "grade", "비대칭 밴드에서 뒤집힘이 안 잡혔다"
