"""seed metric_definition — 루브릭 내보내기 45행

Revision ID: ca31a2180b54
Revises: 9fc8835184c9
Create Date: 2026-09-10

미결 `jin` 23번(+ `jin` 25번 — 항목별 `stat` 코드). 적재 경로(`POST /analyses`
흐름 B)가 `analysis_metric_value.metric_code` 로 이 표를 참조하는데
(`metric_definition` 외래키), 표가 비어 있으면 리포트 적재가 통째로
`UNKNOWN_METRIC_CODE` 로 거부된다.

## 정본은 `agent/`, 여기는 사본이다

행의 정본은 `agent/contracts/metric_definitions.yaml` 이고, 아래 목록은
`agent/scripts/export_metric_definitions.py --json` 의 출력을 그대로 옮긴 것이다.
`agent/` 는 이 패키지에서 임포트할 수 없어(바운디드 컨텍스트 밖) 마이그레이션이
직접 읽지 못하므로 값을 박아 둔다. 루브릭이 바뀌면 다음 명령으로 다시 뽑아
새 마이그레이션을 낸다 — 이 파일을 고치지 않는다.

    python3 agent/scripts/export_metric_definitions.py --json

## 왜 45행인가 — active 루브릭만

- `metric` 12 — 물리량(각도·비율·프레임). `impact_frame` 은 정상호가 행으로
  유지하기로 했다(빠져서 거부되는 쪽이 더 나쁘다).
- `judgment` 1 — `total_score`.
- `grade` 16 · `stat` 16 — 종목·동작·항목별 등급(0/1/2)과 레이더 축 값(0~100).
  `grade.{sport}.{motion}.{id}` / `stat.{sport}.{motion}.{id}`.

draft 루브릭까지 포함하면 73행이지만(`--include-draft`), draft 는 아직 분석에
쓰이지 않으므로 시드하지 않는다. 승격될 때 그 루브릭의 행을 함께 넣는다.

🔴 **부분 시드 금지.** 45행 전량이 아니면 그 코드를 쓰는 리포트가 거부된다.

## 컬럼

`metric_definition` 은 `code`·`label`·`unit` 뿐이다. 내보내기의 `kind`·`note`
는 사람이 표를 읽을 때 쓰라고 붙은 것이라 버린다. 가장 긴 `code` 가 48자로
`String(50)` 에 든다 — 정상호 쪽 `test_no_code_outgrows_the_backend_column` 이
넘지 않도록 고정한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca31a2180b54'
down_revision: Union[str, Sequence[str], None] = '9fc8835184c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `agent/scripts/export_metric_definitions.py --json` 출력 (2026-09-10, active 45행).
# (code, label, unit)
_ROWS: list[tuple[str, str, str]] = [
    ('hip_rotation_range_deg', '골반 회전 범위', 'deg'),
    ('hip_shoulder_separation_deg', '골반-어깨 분리각', 'deg'),
    ('trunk_forward_lean_deg_at_impact', '임팩트 시 몸통 전후 기울기', 'deg'),
    ('support_elbow_angle_at_impact', '임팩트 시 지지 팔 팔꿈치 각', 'deg'),
    ('swing_elbow_angle_at_impact', '임팩트 시 주동 팔 팔꿈치 각', 'deg'),
    ('swing_shoulder_flexion_after_impact_deg', '임팩트 후 주동 어깨 굴곡', 'deg'),
    ('swing_hip_flexion_after_impact_deg', '임팩트 후 주동 고관절 굴곡', 'deg'),
    ('swing_knee_angle_at_impact', '임팩트 시 주동 무릎 각', 'deg'),
    ('plant_knee_angle_at_impact', '임팩트 시 디딤 무릎 각', 'deg'),
    ('plant_foot_to_ball_offset', '디딤발-공 수평 거리', 'ratio'),
    ('follow_through_duration_frames', '팔로스루 지속 시간', 's'),
    ('impact_frame', '임팩트 시각', 's'),
    ('total_score', '종합 점수', 'score'),
    ('grade.baseball.pitching.release_arm_extension', '야구 · 투구 · 공 놓는 순간 팔 뻗기', 'score'),
    ('stat.baseball.pitching.release_arm_extension', '야구 · 투구 · 공 놓는 순간 팔 뻗기', 'score'),
    ('grade.baseball.pitching.hip_shoulder_separation', '야구 · 투구 · 골반이 어깨보다 먼저 열리기', 'score'),
    ('stat.baseball.pitching.hip_shoulder_separation', '야구 · 투구 · 골반이 어깨보다 먼저 열리기', 'score'),
    ('grade.baseball.pitching.stride_leg_block', '야구 · 투구 · 앞다리 버티기', 'score'),
    ('stat.baseball.pitching.stride_leg_block', '야구 · 투구 · 앞다리 버티기', 'score'),
    ('grade.baseball.pitching.trunk_tilt', '야구 · 투구 · 상체 기울기', 'score'),
    ('stat.baseball.pitching.trunk_tilt', '야구 · 투구 · 상체 기울기', 'score'),
    ('grade.baseball.pitching.arm_deceleration', '야구 · 투구 · 던진 뒤 팔 속도 줄이기', 'score'),
    ('stat.baseball.pitching.arm_deceleration', '야구 · 투구 · 던진 뒤 팔 속도 줄이기', 'score'),
    ('grade.basketball.jump_shot.release_arm_extension', '농구 · 점프슛 · 슛하는 팔 뻗기', 'score'),
    ('stat.basketball.jump_shot.release_arm_extension', '농구 · 점프슛 · 슛하는 팔 뻗기', 'score'),
    ('grade.basketball.jump_shot.guide_hand', '농구 · 점프슛 · 공 받치는 손', 'score'),
    ('stat.basketball.jump_shot.guide_hand', '농구 · 점프슛 · 공 받치는 손', 'score'),
    ('grade.basketball.jump_shot.follow_through', '농구 · 점프슛 · 던진 뒤 손목 마무리', 'score'),
    ('stat.basketball.jump_shot.follow_through', '농구 · 점프슛 · 던진 뒤 손목 마무리', 'score'),
    ('grade.basketball.jump_shot.trunk_alignment', '농구 · 점프슛 · 상체 곧게 세우기', 'score'),
    ('stat.basketball.jump_shot.trunk_alignment', '농구 · 점프슛 · 상체 곧게 세우기', 'score'),
    ('grade.basketball.jump_shot.leg_drive', '농구 · 점프슛 · 다리로 밀어 올리기', 'score'),
    ('stat.basketball.jump_shot.leg_drive', '농구 · 점프슛 · 다리로 밀어 올리기', 'score'),
    ('grade.football.instep_shot.plant_knee_flexion', '축구 · 인스텝 슈팅 · 디딤발 무릎 굽히기', 'score'),
    ('stat.football.instep_shot.plant_knee_flexion', '축구 · 인스텝 슈팅 · 디딤발 무릎 굽히기', 'score'),
    ('grade.football.instep_shot.swing_knee_extension', '축구 · 인스텝 슈팅 · 차는 다리 뻗기', 'score'),
    ('stat.football.instep_shot.swing_knee_extension', '축구 · 인스텝 슈팅 · 차는 다리 뻗기', 'score'),
    ('grade.football.instep_shot.trunk_lean', '축구 · 인스텝 슈팅 · 상체 기울기', 'score'),
    ('stat.football.instep_shot.trunk_lean', '축구 · 인스텝 슈팅 · 상체 기울기', 'score'),
    ('grade.football.instep_shot.hip_rotation', '축구 · 인스텝 슈팅 · 골반 돌리기', 'score'),
    ('stat.football.instep_shot.hip_rotation', '축구 · 인스텝 슈팅 · 골반 돌리기', 'score'),
    ('grade.football.instep_shot.follow_through', '축구 · 인스텝 슈팅 · 차고 난 뒤 마무리', 'score'),
    ('stat.football.instep_shot.follow_through', '축구 · 인스텝 슈팅 · 차고 난 뒤 마무리', 'score'),
    ('grade.football.instep_shot.plant_foot_position', '축구 · 인스텝 슈팅 · 디딤발 위치', 'score'),
    ('stat.football.instep_shot.plant_foot_position', '축구 · 인스텝 슈팅 · 디딤발 위치', 'score'),
]


_metric_definition = sa.table(
    "metric_definition",
    sa.column("code", sa.String),
    sa.column("label", sa.String),
    sa.column("unit", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        _metric_definition,
        [{"code": code, "label": label, "unit": unit} for code, label, unit in _ROWS],
    )


def downgrade() -> None:
    # 이 마이그레이션이 넣은 코드만 지운다. 테스트·수동으로 들어온 다른 행은 둔다.
    op.execute(
        _metric_definition.delete().where(
            _metric_definition.c.code.in_([code for code, _, _ in _ROWS])
        )
    )
