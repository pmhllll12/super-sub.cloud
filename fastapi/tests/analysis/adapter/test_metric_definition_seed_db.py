"""`metric_definition` 시드를 실제 PostgreSQL 로 확인한다. 미결 `jin` 23·25번.

리포트 적재(`POST /analyses` 흐름 B)가 `analysis_metric_value.metric_code` 로 이
표를 참조한다 — 외래키라 정의에 없는 코드는 거부된다. **시드가 통째로 비거나
일부만 들어오면 적재가 거부**되므로, 마이그레이션이 넣기로 한 45행이 다 있는지
본다.

정본은 `agent/contracts/metric_definitions.yaml` 이고 라벨·단위는 그쪽이 정한다.
여기서는 **코드 집합과 구조 불변식**만 본다 — 라벨을 여기 박으면 정본이 갈라진다
(미결 `jin` 23번 「하지 말 것」).
"""

from __future__ import annotations

import pytest

from app.analysis.adapter.outbound.orm.metric_definition_orm import (
    MetricDefinitionOrm,
)

pytestmark = pytest.mark.db

# active 루브릭 세 개(야구 투구 · 농구 점프슛 · 축구 인스텝 슈팅)의 항목별 등급 코드.
# 각 항목마다 `grade.*` 와 `stat.*` 가 짝으로 있다(미결 `jin` 25번).
_RUBRIC_CRITERIA = [
    "baseball.pitching.release_arm_extension",
    "baseball.pitching.hip_shoulder_separation",
    "baseball.pitching.stride_leg_block",
    "baseball.pitching.trunk_tilt",
    "baseball.pitching.arm_deceleration",
    "basketball.jump_shot.release_arm_extension",
    "basketball.jump_shot.guide_hand",
    "basketball.jump_shot.follow_through",
    "basketball.jump_shot.trunk_alignment",
    "basketball.jump_shot.leg_drive",
    "football.instep_shot.plant_knee_flexion",
    "football.instep_shot.swing_knee_extension",
    "football.instep_shot.trunk_lean",
    "football.instep_shot.hip_rotation",
    "football.instep_shot.follow_through",
    "football.instep_shot.plant_foot_position",
]

# 물리량 지표(종목 무관) + 총점 + `impact_frame`(정상호가 행으로 유지).
_PHYSICAL_METRICS = [
    "hip_rotation_range_deg",
    "hip_shoulder_separation_deg",
    "trunk_forward_lean_deg_at_impact",
    "support_elbow_angle_at_impact",
    "swing_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg",
    "swing_hip_flexion_after_impact_deg",
    "swing_knee_angle_at_impact",
    "plant_knee_angle_at_impact",
    "plant_foot_to_ball_offset",
    "follow_through_duration_frames",
    "impact_frame",
]


def _expected_codes() -> set[str]:
    codes = set(_PHYSICAL_METRICS)
    codes.add("total_score")
    for crit in _RUBRIC_CRITERIA:
        codes.add(f"grade.{crit}")
        codes.add(f"stat.{crit}")
    return codes


class TestMetricDefinitionSeed:
    def test_active_루브릭_45행이_모두_들어_있다(self, db_session):
        expected = _expected_codes()
        assert len(expected) == 45  # 12 물리량 + total_score + 16 grade + 16 stat

        present = {m.code for m in db_session.query(MetricDefinitionOrm).all()}
        missing = expected - present
        assert not missing, f"시드가 빠뜨린 코드: {sorted(missing)}"

    def test_항목마다_grade_와_stat_이_짝으로_있다(self, db_session):
        """레이더 축(`stat`)과 등급(`grade`)은 같은 항목 집합을 덮어야 한다.

        한쪽만 있으면 그 항목의 리포트 적재가 절반만 성공한다.
        """
        codes = {m.code for m in db_session.query(MetricDefinitionOrm).all()}
        grades = {c[len("grade.") :] for c in codes if c.startswith("grade.")}
        stats = {c[len("stat.") :] for c in codes if c.startswith("stat.")}
        assert grades == stats
        assert set(_RUBRIC_CRITERIA) <= grades

    def test_총점이_metrics_행으로_있다(self, db_session):
        """계약 3-1 — 총점과 항목별 등급도 `metrics[]` 에 넣는다."""
        assert db_session.get(MetricDefinitionOrm, "total_score") is not None

    def test_어느_코드도_컬럼_폭을_넘지_않는다(self, db_session):
        """`analysis_metric_value.metric_code` 는 `String(50)`. 넘으면 잘려서
        다른 코드와 충돌한다. 정상호 쪽 `test_no_code_outgrows_the_backend_column`
        과 같은 방어를 실제 적재된 데이터에도 건다.
        """
        too_long = [
            m.code
            for m in db_session.query(MetricDefinitionOrm).all()
            if len(m.code) > 50
        ]
        assert not too_long, f"50자를 넘는 코드: {too_long}"
