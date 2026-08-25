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
from supersub_agent.scoring import load_rubric

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


def test_pipeline_covers_every_rubric_metric():
    """루브릭이 요구하는 지표를 파이프라인이 전부 산출하는지 —
    두 파일이 따로 수정돼 어긋나는 것을 막는 계약 테스트."""
    rubric = load_rubric("rubrics/football_instep_shot.yaml")
    feats = extract_features(build_sequence())
    F.verify_rubric_coverage(rubric, feats)
