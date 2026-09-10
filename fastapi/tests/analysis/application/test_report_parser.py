"""`parse_report` 는 순수 함수라 픽스처 JSON 하나로 전수 검사한다. 미결 `jin` 27번.

계약은 `agent/contracts/report_schema.yaml`(정상호). 여기서는 그 계약대로 온
봉투가 우리 행 모양으로 정확히 옮겨지는지 본다.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from app.analysis.application.use_cases.report_parser import (
    MalformedReport,
    UnsupportedReportSchema,
    parse_report,
)

# football.instep_shot — 시드된 코드만 쓴다(마이그레이션 ca31a2180b54).
# schema_version 은 계약 현재값 "1.1" (ho 476b0df — view_dependent 추가로 minor 상승).
_ENVELOPE = {
    "schema_version": "1.1",
    "source_video": "s3://b/videos/u/v.mp4",
    "video_id": "11111111-1111-4111-8111-111111111111",
    "analyzed_at": "20260910T120000Z",
    "code_version": "abc1234",
    "rubric": {
        "sport": "football",
        "motion": "instep_shot",
        "version": "0.1",
        "path": "rubrics/football_instep_shot.yaml",
        "impact_limb": "right_leg",
        "impact_event": "ball_contact",
    },
    "swing_side": "right",
    "sampled_fps": 30.0,
    "frames": 300,
    "frame_metrics_seconds": {"impact_frame": 2.07},
    "judge_model": "exaone-4.0-1.2b",
    "previews": {"impact": "s3://b/reports/u/v/impact.png"},
    "keypoint_quality": {
        "known": True,
        "limb": "leg",
        "side": "auto",
        "swing_side_valid_ratio": 0.94,
        "gate_joints": 3,
        "threshold": 0.7,
        "min_keypoint_confidence": 0.3,
    },
    "features": {
        "trunk_forward_lean_deg_at_impact": 12.4,
        "plant_knee_angle_at_impact": 158.0,
        "impact_frame": 62,  # 🔴 프레임 원값 — frame_metrics_seconds 로 덮여야
    },
    "result": {
        "score": 71,
        "grade": "B",
        "summary": "디딤발 무릎 굽히기가 강점입니다.",
        "pipeline_version": "pose-v0.1",
        "rubric_version": "0.1",
        "provisional": True,
        "breakdown": [
            {
                "criterion_id": "plant_knee_flexion",
                "name": "디딤발 무릎 굽히기",
                "grade": 2,
                "weight": 0.15,
                "contribution": 15.0,
                "title": "흔들리지 않는 축",
                "band": "150~170",
                "out_of_band": "",
                "stat": 88.5,
                "evidence": "디딤발이 공 옆에 안정적으로 놓였습니다.",
                "metric_ref": "plant_knee_angle_at_impact",
            },
            {
                "criterion_id": "trunk_lean",
                "name": "상체 기울기",
                "grade": 0,
                "weight": 0.20,
                "contribution": 0.0,
                "title": "젖혀진 상체",
                "band": "5~20",
                "out_of_band": "",
                "stat": None,  # stat 없으면 stat.* 행을 안 만든다
                "evidence": "상체가 뒤로 젖혀졌습니다.",
                "metric_ref": "trunk_forward_lean_deg_at_impact",
            },
        ],
        "skipped": [
            {"criterion_id": "plant_foot_position", "name": "디딤발 위치", "weight": 0.15},
        ],
    },
}


def _raw(env=None) -> bytes:
    return json.dumps(env or _ENVELOPE).encode()


def test_봉투를_행_모양으로_옮긴다():
    p = parse_report(_raw())
    assert p.schema_version == "1.1"
    assert (p.rubric_sport, p.rubric_motion, p.rubric_version) == (
        "football",
        "instep_shot",
        "0.1",
    )
    assert p.pipeline_version == "pose-v0.1"
    assert p.model_name == "exaone-4.0-1.2b"
    assert p.provisional is True
    assert p.previews == {"impact": "s3://b/reports/u/v/impact.png"}
    assert p.keypoint_quality["swing_side_valid_ratio"] == 0.94


def test_frame_metrics_seconds_가_features_원값을_덮는다():
    p = parse_report(_raw())
    impact = next(v for v in p.metric_values if v.metric_code == "impact_frame")
    assert impact.value == Decimal("2.07")  # 62(프레임) 가 아니라


def test_총점과_항목별_등급_stat_이_metric_value_로_간다():
    p = parse_report(_raw())
    codes = {v.metric_code: v.value for v in p.metric_values}
    assert codes["total_score"] == Decimal("71")
    assert codes["grade.football.instep_shot.plant_knee_flexion"] == Decimal("2")
    assert codes["stat.football.instep_shot.plant_knee_flexion"] == Decimal("88.5")
    # stat 이 None 이면 stat.* 행이 없다
    assert "stat.football.instep_shot.trunk_lean" not in codes
    assert codes["grade.football.instep_shot.trunk_lean"] == Decimal("0")


def test_breakdown_과_skipped_가_criterion_행으로():
    p = parse_report(_raw())
    by_id = {c.criterion_id: c for c in p.criteria}
    assert by_id["plant_knee_flexion"].skipped is False
    assert by_id["plant_knee_flexion"].title == "흔들리지 않는 축"
    assert by_id["plant_knee_flexion"].grade == 2

    sk = by_id["plant_foot_position"]
    assert sk.skipped is True
    assert sk.grade is None and sk.title is None and sk.evidence is None
    assert sk.weight == Decimal("0.15")  # 루브릭 원값


def test_모르는_schema_major_는_거부한다():
    bad = {**_ENVELOPE, "schema_version": "2.0"}
    with pytest.raises(UnsupportedReportSchema):
        parse_report(_raw(bad))


def test_minor_버전_차이는_통과한다():
    # 낡은 봉투("1.0")와 앞선 minor("1.7") 둘 다 통과한다 — major 만 본다
    # (정상호: "1.0 봉투와 1.1 봉투가 섞여도 둘 다 유효").
    for v in ("1.0", "1.7"):
        parse_report(_raw({**_ENVELOPE, "schema_version": v}))  # 예외 없음


def test_JSON_이_아니면_MalformedReport():
    with pytest.raises(MalformedReport):
        parse_report(b"not json{{")


def test_필수_키가_없으면_MalformedReport():
    no_result = {k: v for k, v in _ENVELOPE.items() if k != "result"}
    with pytest.raises(MalformedReport):
        parse_report(_raw(no_result))
