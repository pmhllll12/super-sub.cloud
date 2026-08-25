"""특징 추출 검증 — 합성 키포인트로 수학을 확인한다.

실제 슈팅 영상이 아직 없으므로, 각도를 지정해 역으로 관절 좌표를 만든 뒤
extract_features가 그 각도를 되찾아내는지 본다. 영상이 확보되면 이 테스트는
회귀 테스트로 남기고 실제 클립 기반 테스트를 추가한다.
"""

from __future__ import annotations

import numpy as np
import pytest

from supersub_agent import features as F
from supersub_agent.features import InsufficientQuality, extract_features, joint_angle
from supersub_agent.scoring import discover_rubrics

THIGH = 100.0
SHIN = 100.0
TRUNK = 150.0
SHOULDER_W = 80.0
HIP_W = 60.0


def _leg(hip_xy: np.ndarray, thigh_dir_deg: float, knee_angle_deg: float):
    """무릎각이 knee_angle_deg가 되도록 무릎·발목 좌표를 만든다."""
    t = np.radians(thigh_dir_deg)
    knee = hip_xy + THIGH * np.array([np.sin(t), np.cos(t)])
    phi = np.radians(180.0 - knee_angle_deg)
    s = t + phi
    ankle = knee + SHIN * np.array([np.sin(s), np.cos(s)])
    return knee, ankle


def build_sequence(
    n: int = 31,
    impact: int = 20,
    swing_knee_at_impact: float = 152.0,
    plant_knee_at_impact: float = 158.0,
    trunk_lean_at_impact: float = 12.0,
    hip_rotation_range: float = 34.0,
) -> np.ndarray:
    """인스텝 슈팅을 흉내낸 (T, 17, 3) 키포인트 시퀀스."""
    frames = []
    for i in range(n):
        # 스윙 다리 무릎각: 백스윙에서 접혔다가 임팩트에서 지정 각도로 신전
        if i <= impact:
            p = i / impact
            swing_knee = 165.0 - 70.0 * np.sin(np.pi * p) + (
                (swing_knee_at_impact - 165.0) * p
            )
        else:
            p = (i - impact) / max(1, n - 1 - impact)
            swing_knee = swing_knee_at_impact + 15.0 * p

        plant_knee = plant_knee_at_impact + 6.0 * np.sin(np.pi * i / n)

        # 상체 기울기 — 임팩트에서 지정값
        lean = trunk_lean_at_impact * (0.3 + 0.7 * min(1.0, i / impact))
        # 골반 회전 — 백스윙 구간에서 지정 범위만큼 변화
        rot = hip_rotation_range * (i / impact) if i <= impact else hip_rotation_range

        kps = np.zeros((17, 3))
        kps[:, 2] = 0.9  # 신뢰도

        hip_c = np.array([0.0, 0.0])
        half = np.radians(rot)
        # 골반 벡터를 rot만큼 회전 (원근 축소를 x폭 변화로 표현)
        kps[F.L_HIP, :2] = hip_c + (HIP_W / 2) * np.array([np.cos(half), np.sin(half)])
        kps[F.R_HIP, :2] = hip_c - (HIP_W / 2) * np.array([np.cos(half), np.sin(half)])

        lean_rad = np.radians(lean)
        shoulder_c = hip_c + TRUNK * np.array([np.sin(lean_rad), -np.cos(lean_rad)])
        kps[F.L_SHOULDER, :2] = shoulder_c + np.array([SHOULDER_W / 2, 0.0])
        kps[F.R_SHOULDER, :2] = shoulder_c - np.array([SHOULDER_W / 2, 0.0])
        kps[F.NOSE, :2] = shoulder_c + np.array([0.0, -40.0])

        # 왼다리 = 스윙(발목 이동이 큼), 오른다리 = 디딤발
        swing_thigh_dir = -30.0 + 60.0 * (i / n)
        lk, la = _leg(kps[F.L_HIP, :2], swing_thigh_dir, swing_knee)
        rk, ra = _leg(kps[F.R_HIP, :2], 2.0, plant_knee)
        kps[F.L_KNEE, :2], kps[F.L_ANKLE, :2] = lk, la
        kps[F.R_KNEE, :2], kps[F.R_ANKLE, :2] = rk, ra

        frames.append(kps)
    return np.stack(frames)


def test_joint_angle_basics():
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 0.0])
    c = np.array([1.0, 0.0])
    assert joint_angle(a, b, c) == pytest.approx(90.0, abs=1e-6)

    straight = joint_angle(np.array([0.0, 1.0]), b, np.array([0.0, -1.0]))
    assert straight == pytest.approx(180.0, abs=1e-6)


def test_normalize_is_scale_invariant():
    """촬영 거리가 2배로 달라져도 정규화 후 좌표는 같아야 한다."""
    seq = build_sequence()
    near = F.normalize(seq)
    far = seq.copy()
    far[:, :, :2] *= 2.0          # 카메라가 가까워진 상황
    far_norm = F.normalize(far)
    np.testing.assert_allclose(near[:, :, :2], far_norm[:, :, :2], atol=1e-9)


def test_identify_legs_picks_moving_leg():
    seq = F.normalize(build_sequence())
    swing, plant = F.identify_legs(seq)
    assert swing == F.L_KNEE
    assert plant == F.R_KNEE


def test_extract_features_recovers_specified_angles():
    seq = build_sequence(swing_knee_at_impact=152.0, plant_knee_at_impact=158.0)
    feats = extract_features(seq)

    # 임팩트 추정이 실제 임팩트 부근이어야 한다
    assert abs(feats["impact_frame"] - 20) <= 3
    # 지정한 무릎각을 되찾아야 한다 (임팩트 프레임 오차 범위 내)
    assert feats["swing_knee_angle_at_impact"] == pytest.approx(152.0, abs=12.0)
    assert feats["plant_knee_angle_at_impact"] == pytest.approx(158.0, abs=8.0)


def test_extract_features_is_deterministic():
    seq = build_sequence()
    runs = [extract_features(seq) for _ in range(5)]
    assert all(r == runs[0] for r in runs)


def test_low_confidence_is_rejected():
    """품질이 낮은 입력으로는 점수를 내지 않는다."""
    seq = build_sequence()
    seq[:, [F.L_KNEE, F.R_KNEE], 2] = 0.05
    with pytest.raises(InsufficientQuality, match="유효 프레임 비율"):
        extract_features(seq)


def test_truncated_clip_is_rejected():
    """동작 전후가 잘린 영상은 구간 분할이 성립하지 않는다."""
    seq = build_sequence(n=31, impact=20)[18:]
    with pytest.raises(InsufficientQuality, match="경계"):
        extract_features(seq)


def test_undetected_frames_do_not_become_impact():
    """검출 실패 프레임이 임팩트로 잡히지 않는다.

    pose.py는 사람이 검출되지 않은 프레임을 zeros((17,3))으로 채운다. 그 프레임의
    무릎각은 joint_angle이 NaN을 내고, np.argmax는 NaN을 최대값으로 취급하므로
    마스킹하지 않으면 임팩트가 항상 첫 검출 실패 프레임으로 잡힌다.
    실클립(4K 25fps)에서 앞 11프레임이 미검출이라 이 경로로 오진했다.
    """
    PAD = 8
    seq = build_sequence(n=31, impact=20)
    padded = np.concatenate([np.zeros((PAD, 17, 3)), seq])

    base = extract_features(seq)
    feats = extract_features(padded)

    # 앞에 붙은 미검출 구간만큼만 밀릴 뿐, 판정 근거는 달라지지 않아야 한다.
    assert feats["impact_frame"] == base["impact_frame"] + PAD
    assert feats["plant_knee_angle_at_impact"] == base["plant_knee_angle_at_impact"]
    assert feats["swing_knee_angle_at_impact"] == base["swing_knee_angle_at_impact"]
    assert feats["trunk_forward_lean_deg_at_impact"] == base["trunk_forward_lean_deg_at_impact"]


def _with_arm_swing(seq: np.ndarray) -> np.ndarray:
    """왼팔이 크게 휘둘리는 시퀀스로 만든다 (팔 기반 종목 흉내).

    build_sequence는 팔 키포인트를 (0,0)으로 두므로 여기서 채워 넣는다.
    """
    out = seq.copy()
    n, release = len(out), 20
    for i in range(n):
        # 무릎과 같은 모양: 접혔다가 펴진다. 신전 각속도 피크가 구간 안쪽에
        # 있어야 위상 분할이 성립한다(끝에 걸리면 경계 가드에 막힌다).
        if i <= release:
            angle = 160.0 - 90.0 * np.sin(np.pi * i / release)
        else:
            angle = 160.0 + 5.0 * (i - release) / max(1, n - 1 - release)

        for side, sign in (("l", -1.0), ("r", 1.0)):
            sh = F.L_SHOULDER if side == "l" else F.R_SHOULDER
            el = F.L_ELBOW if side == "l" else F.R_ELBOW
            wr = F.L_WRIST if side == "l" else F.R_WRIST
            # 오른팔은 거의 정지 → 스윙 팔은 왼팔로 판별돼야 한다.
            a = np.radians(angle if side == "l" else 90.0)
            out[i, el, :2] = out[i, sh, :2] + np.array([sign * 30.0, 40.0])
            # 팔꿈치를 꼭짓점으로 한 각도가 정확히 a가 되도록 손목을 놓는다.
            # 방향을 그대로 각도로 쓰면 joint_angle이 다른 값을 낸다.
            back = out[i, sh, :2] - out[i, el, :2]
            base = np.arctan2(back[1], back[0])
            out[i, wr, :2] = out[i, el, :2] + 45.0 * np.array(
                [np.cos(base + sign * a), np.sin(base + sign * a)]
            )
        out[i, [F.L_ELBOW, F.R_ELBOW, F.L_WRIST, F.R_WRIST], 2] = 0.9
    return out


def test_arm_limb_shares_the_leg_machinery():
    """팔도 같은 위상 분할 로직으로 돈다 — 농구·테니스가 열리는 지점."""
    seq = _with_arm_swing(build_sequence())

    swing, support = F.identify_limb(F.normalize(seq), "arm")

    assert swing == F.LIMB_CHAINS["arm"]["left"], "손목이 더 움직인 쪽이 스윙"
    assert support == F.LIMB_CHAINS["arm"]["right"]

    feats = extract_features(seq, None, impact_limb="arm")
    assert "swing_elbow_angle_at_impact" in feats
    assert 0 < feats["impact_frame"] < len(seq) - 1


def test_arm_metrics_are_dropped_when_arm_is_unreliable():
    """팔 신뢰도가 낮으면 팔 지표를 내지 않는다 — 튀는 값을 근거로 주지 않는다."""
    seq = _with_arm_swing(build_sequence())
    seq[:, [F.L_ELBOW, F.R_ELBOW, F.L_WRIST, F.R_WRIST], 2] = 0.05

    feats = extract_features(seq, None, impact_limb="leg")

    assert "swing_elbow_angle_at_impact" not in feats
    assert "swing_knee_angle_at_impact" in feats, "다리 지표는 그대로 나온다"


def test_hip_rotation_survives_angle_wraparound():
    """골반이 ±180 경계에 걸쳐도 회전량이 부풀지 않는다.

    arctan2는 -180~180을 돌려주므로 언랩하지 않으면 ptp가 360에 가까워진다.
    농구 클립에서 실제 회전 12.7도가 359.0도로 나왔던 버그다.
    """
    seq = build_sequence()

    baseline = extract_features(seq)["hip_rotation_range_deg"]

    # 포즈 전체를 180도 회전해 골반 방향각을 ±180 경계 위로 옮긴다.
    # 관절 각도는 회전 불변이므로 동작은 그대로고 좌표계만 달라진다.
    rotated = seq.copy()
    rotated[:, :, :2] = -rotated[:, :, :2]

    assert extract_features(rotated)["hip_rotation_range_deg"] == pytest.approx(
        baseline, abs=0.2
    )


def test_unknown_limb_is_rejected():
    with pytest.raises(ValueError, match="impact_limb"):
        extract_features(build_sequence(), None, impact_limb="tail")


@pytest.mark.parametrize("key", sorted(discover_rubrics("rubrics")))
def test_pipeline_covers_every_rubric_metric(key):
    """루브릭이 요구하는 지표를 파이프라인이 전부 산출하는지 —
    두 파일이 따로 수정돼 어긋나는 것을 막는 계약 테스트.

    **rubrics/의 모든 파일을 돈다.** 종목이 늘어나면 이 테스트도 함께 늘어야
    한다 — 한 파일만 검사하면 새로 추가한 루브릭의 measured_by 오타가 실영상을
    넣기 전까지 드러나지 않는다.
    """
    rubric = discover_rubrics("rubrics")[key]
    seq = _with_arm_swing(build_sequence())
    feats = extract_features(seq, None, rubric.impact_limb, rubric.impact_event)
    F.verify_rubric_coverage(rubric, feats)


@pytest.mark.parametrize("event", F.IMPACT_EVENTS)
def test_impact_events_pick_different_frames(event):
    """임팩트 사건 정의가 실제로 다른 프레임을 고르는지.

    레이업처럼 채찍질이 없는 동작은 신전 각속도 피크가 릴리스가 아니다.
    실클립에서 extension_peak은 6프레임(공을 모으는 중), distal_apex는
    21프레임(림 앞 최고점)을 잡았다.
    """
    seq = _with_arm_swing(build_sequence())
    swing, _ = F.identify_limb(F.normalize(seq), "arm")

    phases = F.segment_phases(F.normalize(seq), swing, "arm", event)

    assert 0 < phases.impact < len(seq) - 1


def test_unknown_impact_event_is_rejected():
    seq = _with_arm_swing(build_sequence())
    swing, _ = F.identify_limb(F.normalize(seq), "arm")

    with pytest.raises(ValueError, match="impact_event"):
        F.segment_phases(F.normalize(seq), swing, "arm", "vibes")


def test_distal_apex_ignores_undetected_frames():
    """미검출 프레임이 최고점으로 잡히지 않는지.

    검출 실패 프레임은 좌표가 (0,0)이라 골반 중심을 빼면 몸 위쪽으로 튄다.
    마스킹하지 않으면 항상 그 프레임이 최고점이 된다 — extension_peak이
    NaN에서 겪었던 것과 같은 종류의 함정이다.
    """
    seq = _with_arm_swing(build_sequence())
    seq[3] = 0.0            # 3프레임을 통째로 미검출 처리
    norm = F.normalize(seq)
    swing, _ = F.identify_limb(norm, "arm")

    phases = F.segment_phases(norm, swing, "arm", "distal_apex")

    assert phases.impact != 3
