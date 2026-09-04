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
    """팔도 같은 위상 분할 로직으로 돈다 — 농구·야구가 열리는 지점."""
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


def _hide_support_arm(seq: np.ndarray, noise: float = 60.0) -> np.ndarray:
    """지지(오른) 팔을 가려진 것처럼 만든다 — 낮은 신뢰도 + 튀는 좌표.

    야구 투구 실클립의 글러브 팔이 이렇다. 와인드업에서 글러브가 반대쪽 손을
    덮어 신뢰도가 0.3~0.6으로 떨어지고, 그 프레임의 좌표는 프레임마다 튄다.
    """
    out = seq.copy()
    rng = np.random.default_rng(0)
    joints = [F.R_SHOULDER, F.R_ELBOW, F.R_WRIST]
    hidden = np.flatnonzero(np.arange(len(out)) % 2 == 1)   # 절반이 가려진다
    idx = np.ix_(hidden, joints)
    coords = out[idx]
    coords[:, :, :2] += rng.normal(0.0, noise, (len(hidden), len(joints), 2))
    coords[:, :, 2] = 0.35
    out[idx] = coords
    return out


def test_gate_looks_at_the_swing_side_only():
    """지지 팔이 가려져도 스윙 팔이 보이면 분석한다.

    야구 투구 실클립(투구 구간 3.6초)에서 던지는 팔은 98%인데 글러브 팔이 50%라
    양쪽을 함께 요구하면 48%로 반려됐다. 투구 루브릭이 쓰는 지표는 모두 던지는
    팔에서 나오므로, 쓰지도 않는 팔 때문에 입력을 버리게 된다.
    """
    seq = _hide_support_arm(_with_arm_swing(build_sequence()))

    assert F.check_quality(seq, limb="arm", side="left") >= 0.7

    feats = extract_features(seq, None, impact_limb="arm", swing_side="left")
    assert "swing_elbow_angle_at_impact" in feats
    assert "support_elbow_angle_at_impact" not in feats, "가려진 팔 지표는 빠진다"


def _thin_out(seq: np.ndarray, joints: list[int], ratio: float = 0.5) -> np.ndarray:
    """해당 관절을 일정 비율의 프레임에서만 검출된 것으로 만든다.

    전 구간을 0으로 만들지 않는 이유는 실제 상황이 그렇지 않아서다 — 손목은
    가려졌다 보였다 한다. 완전히 0이면 게이트를 통과해도 임팩트를 못 찾는다.
    """
    out = seq.copy()
    hidden = np.arange(len(out)) % 2 == 1 if ratio == 0.5 else \
        np.arange(len(out)) >= int(len(out) * ratio)
    out[np.ix_(np.flatnonzero(hidden), joints)] = np.concatenate(
        [out[np.ix_(np.flatnonzero(hidden), joints)][:, :, :2],
         np.zeros((int(hidden.sum()), len(joints), 1))], axis=2
    )
    return out


def test_arm_gate_passes_when_only_the_wrist_is_thin():
    """팔: 어깨·팔꿈치가 충분하면 손목이 부족해도 통과한다.

    손목은 팔 루브릭에서 팔꿈치각 하나에만 쓰인다. 전 구간 70%를 요구하면 그
    지표 하나 때문에 나머지를 통째로 버린다 — 야구 3,444클립에서 21.1%→70.8%,
    농구 134클립에서 11.2%→39.6%로 갈린 지점이다.
    """
    seq = _thin_out(_with_arm_swing(build_sequence()), [F.L_WRIST])

    swing = F.LIMB_CHAINS["arm"]["left"]
    assert F.valid_frames(seq, "arm", swing).mean() < 0.7, "손목까지 보면 미달"
    assert F.check_quality(seq, limb="arm", side="left") >= 0.7

    feats = extract_features(seq, None, impact_limb="arm", swing_side="left")
    assert "swing_elbow_angle_at_impact" in feats, "손목이 유효한 프레임에서 나온다"


def test_arm_gate_still_fails_when_the_elbow_is_thin():
    """팔: 팔꿈치가 부족하면 여전히 막는다 — 게이트가 느슨해지면 안 된다."""
    seq = _thin_out(_with_arm_swing(build_sequence()), [F.L_ELBOW])

    with pytest.raises(InsufficientQuality, match="유효 프레임 비율"):
        F.check_quality(seq, limb="arm", side="left")


def _mirror_legs(seq: np.ndarray) -> np.ndarray:
    """다리 좌우를 통째로 맞바꾼다 — 스윙 다리가 오른쪽인 시퀀스를 만든다.

    build_sequence는 스윙 팔도 스윙 다리도 왼쪽이라 둘을 구별할 수 없다.
    실제 동작은 반대쪽인 경우가 많다(오른손 투수의 디딤발은 왼발).
    """
    out = seq.copy()
    out[:, [F.L_HIP, F.R_HIP]] = out[:, [F.R_HIP, F.L_HIP]]
    out[:, [F.L_KNEE, F.R_KNEE]] = out[:, [F.R_KNEE, F.L_KNEE]]
    out[:, [F.L_ANKLE, F.R_ANKLE]] = out[:, [F.R_ANKLE, F.L_ANKLE]]
    return out


def test_manual_side_applies_to_the_impact_limb_only():
    """수동 side는 impact_limb에만 적용된다 — **버그가 아니라 의도다.**

    "왼쪽"이 팔과 다리에서 같은 것을 가리키지 않는다. 오른손 투수의 디딤발은
    왼발이고, 오른발 인스텝 슈팅에서 크게 도는 팔은 왼팔이다. 사람이 아는 값은
    동작을 정의하는 사지 한쪽("던지는 팔은 왼쪽")뿐이며, 그 값을 반대쪽 사지에
    그대로 넘기면 상당수 동작에서 **정확히 틀린 쪽**을 지정하게 된다. 평가셋
    39클립에서 자동 판별된 팔 측과 다리 측은 44%에서만 일치했다 — 한 값이
    둘을 대신할 수 없다는 뜻이다.

    이 테스트는 "일관성"을 이유로 반대쪽까지 전달하는 변경을 막는다.
    """
    # 스윙 팔은 왼쪽, 스윙 다리는 오른쪽 — 반대쪽인 실제 동작을 흉내낸다.
    seq = _mirror_legs(_with_arm_swing(build_sequence()))
    norm = F.normalize(seq)
    assert F.identify_limb(norm, "arm")[0] == F.LIMB_CHAINS["arm"]["left"]
    assert F.identify_legs(norm)[0] == F.R_KNEE, "자동 판별로는 오른 다리가 스윙"

    feats = extract_features(seq, None, impact_limb="arm", swing_side="left")
    t = feats["impact_frame"]

    # 다리는 side="left"를 받지 않았으므로 auto 판별 그대로 오른 다리다.
    right_knee = F.chain_series(norm, F.LIMB_CHAINS["leg"]["right"])[t]
    left_knee = F.chain_series(norm, F.LIMB_CHAINS["leg"]["left"])[t]
    assert feats["swing_knee_angle_at_impact"] == pytest.approx(right_knee, abs=0.05)
    assert feats["plant_knee_angle_at_impact"] == pytest.approx(left_knee, abs=0.05)


def test_leg_gate_still_requires_the_ankle():
    """다리: 발목이 부족하면 막는다 — 팔과 달리 여기서는 뺄 수 없다.

    무릎각이 joint_angle(엉덩이, 무릎, 발목)이라 발목이 빠지면 각도 자체가
    NaN이 되고, 임팩트를 그 각도의 신전 각속도 피크로 정의하므로 임팩트마저
    못 찾는다. 축구 17건에서 발목 신뢰도를 0으로 만들자 17/17 전부 실패했다.
    """
    seq = _thin_out(build_sequence(), [F.L_ANKLE, F.R_ANKLE])

    hip_knee = F.LIMB_CHAINS["leg"]["left"][:2]
    assert F.valid_frames(seq, "leg", hip_knee).mean() >= 0.7, "엉덩이·무릎은 충분"

    with pytest.raises(InsufficientQuality, match="유효 프레임 비율"):
        F.check_quality(seq, limb="leg")


def test_leg_gate_passes_on_normal_input():
    """다리: 세 관절이 모두 충분하면 그대로 통과한다."""
    seq = build_sequence()

    assert F.check_quality(seq, limb="leg") >= 0.7
    assert "swing_knee_angle_at_impact" in extract_features(seq)


def test_swing_side_can_be_given_explicitly():
    """스윙 측을 지정하면 자동 판별을 쓰지 않는다.

    자동 판별은 이동량으로 고르는데 팔 종목에서 약하다 — 야구 투구 실클립에서
    던지는 왼팔 18.2 대 글러브 오른팔 27.6으로 뒤집혔고, 농구 레이업은 16.30
    대 16.09로 1% 차이였다(identify_limb 참고). 던지는 팔을 아는 사람이
    지정하면 그 실패가 사라진다.
    """
    # 오른팔이 크게 튀어 자동 판별이 오른팔을 스윙으로 집는 시퀀스.
    seq = _hide_support_arm(_with_arm_swing(build_sequence()), noise=200.0)
    norm = F.normalize(seq)
    assert F.identify_limb(norm, "arm")[0] == F.LIMB_CHAINS["arm"]["right"]

    swing, support = F.identify_limb(norm, "arm", "left")

    assert swing == F.LIMB_CHAINS["arm"]["left"]
    assert support == F.LIMB_CHAINS["arm"]["right"]


def test_unknown_swing_side_is_rejected():
    with pytest.raises(ValueError, match="side"):
        F.identify_limb(F.normalize(build_sequence()), "leg", "왼쪽")


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


def test_hip_rotation_survives_left_right_label_swap():
    """좌우 골반 라벨이 뒤바뀌어도 회전량이 180도 부풀지 않는다.

    몸이 돌아 등을 보이면 포즈 모델의 좌/우 배정이 뒤집힌다. 골반을 벡터로
    다루면 그 순간 각도가 180도 점프한다 — 야구 투구 실클립에서 프레임 6→7에
    -4.5도 → -183.8도로 뛰었고, 실제 회전 83도가 181.1도로 부풀어 **오측정이
    최고 등급 장점으로 표시됐다.** 골반은 방향이 아니라 축이다.
    """
    seq = build_sequence()
    vec = seq[:, F.L_HIP, :2] - seq[:, F.R_HIP, :2]

    # 축 각도는 양 끝점을 맞바꿔도 그대로다.
    assert F._axis_deg(vec) == pytest.approx(F._axis_deg(-vec))

    swapped = seq.copy()
    half = len(swapped) // 2
    swapped[half:, [F.L_HIP, F.R_HIP]] = swapped[half:, [F.R_HIP, F.L_HIP]]

    # 스왑은 다리 체인의 몸통쪽 관절을 바꾸므로 임팩트 프레임이 조금 달라지고,
    # 그만큼 구간도 달라진다. 여기서 막으려는 것은 그 오차가 아니라 **180도가
    # 통째로 실리는 것**이다.
    swapped_range = extract_features(swapped)["hip_rotation_range_deg"]
    assert swapped_range < 90.0, f"라벨 스왑이 회전량에 실렸다: {swapped_range}"


def test_separation_is_dropped_when_torso_faces_the_camera():
    """몸통이 정면이면 분리각을 내지 않는다 — 잴 수 없는 값을 만들지 않는다.

    투영된 축이 짧아질수록 각도는 작은 오차에도 크게 흔들린다. 야구 투구
    실클립에서 골반 축 길이가 0.44로 줄어든 프레임이 분리각 81.2도를 냈다
    (축이 제대로 보이는 프레임에서는 49.9도).
    """
    seq = build_sequence()
    assert "hip_shoulder_separation_deg" in extract_features(seq)

    # 골반 두 점을 중앙으로 모아 축을 짧게 만든다 = 골반이 카메라를 향한 상태.
    # 어깨는 정규화 스케일(어깨너비 중앙값)이라 함께 줄이면 상쇄되므로 놔둔다.
    facing = seq.copy()
    mid = (facing[:, F.L_HIP, :2] + facing[:, F.R_HIP, :2]) / 2.0
    for j in (F.L_HIP, F.R_HIP):
        facing[:, j, :2] = mid + (facing[:, j, :2] - mid) * 0.2

    feats = extract_features(facing)
    assert "hip_shoulder_separation_deg" not in feats
    assert "swing_knee_angle_at_impact" in feats, "다리 지표는 그대로 나온다"


def test_implausible_measurements_are_dropped_not_graded():
    """물리적으로 불가능한 값은 0등급이 아니라 미측정으로 빠진다.

    닫힌 밴드만으로는 부족하다 — 범위 밖 값을 0등급으로 떨어뜨리면 측정이 깨진
    것을 "못한 것"으로 채점하게 된다. 촬영 조건으로 선수를 감점하지 않는다는
    원칙(도구 미검출 처리)이 여기에도 적용된다.
    """
    ok = {"hip_rotation_range_deg": 34.0, "swing_knee_angle_at_impact": 152.0}
    assert F._drop_implausible(dict(ok)) == ok

    broken = {**ok, "hip_rotation_range_deg": 181.1}
    dropped = F._drop_implausible(broken)

    assert "hip_rotation_range_deg" not in dropped
    assert dropped["swing_knee_angle_at_impact"] == 152.0, "나머지는 남는다"


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


# --- 프레임 단위 지표의 물리 시간 표기 (미결 7번 E-3) ----------------------


def test_every_frame_valued_metric_is_declared():
    """🔴 **이 검사가 E-3의 본체다.**

    프레임 단위 지표를 새로 만들고 선언을 빼먹으면, 그 값은 격자 정보 없이
    밖으로 나간다 — 그것이 이 결함이 생긴 방식이다. 이름으로 걸러 잡는다.

    이름이 `_frame`/`_frames`로 끝나지 않는 프레임 단위 지표를 만들면 이
    검사는 못 잡는다. 그래서 **이름 규약도 함께 강제한다**(아래 반대 방향).
    """
    feats = extract_features(build_sequence())
    declared = F.FRAME_INDEX_METRICS | F.FRAME_DURATION_METRICS

    by_name = {k for k in feats if k.endswith(("_frame", "_frames"))}
    assert by_name <= declared, (
        f"프레임 단위로 보이는데 선언되지 않았다: {sorted(by_name - declared)}. "
        "FRAME_INDEX_METRICS 또는 FRAME_DURATION_METRICS 에 넣을 것"
    )
    # 반대 방향 — 선언해 놓고 이름이 규약을 벗어나면 다음 사람이 못 찾는다.
    assert all(k.endswith(("_frame", "_frames")) for k in declared)

    # 두 목록은 겹치지 않는다. 인덱스와 길이는 뜻이 다르다.
    assert not (F.FRAME_INDEX_METRICS & F.FRAME_DURATION_METRICS)


def test_frame_metrics_are_converted_with_the_effective_fps():
    feats = {"impact_frame": 62, "follow_through_duration_frames": 8}

    # 실효 25fps: 62/25 = 2.48초, 8/25 = 0.32초
    assert F.frame_metrics_as_seconds(feats, 25.0) == {
        "impact_frame": 2.48,
        "follow_through_duration_frames": 0.32,
    }
    # 같은 프레임 번호가 다른 격자에서는 다른 순간이다 — 이것이 요점이다.
    assert F.frame_metrics_as_seconds(feats, 12.5)["impact_frame"] == 4.96


def test_unknown_grid_yields_no_seconds_instead_of_a_made_up_number():
    """🔴 모르면 지어내지 않는다. 그럴듯한 기본값이 이 결함의 원인이었다."""
    feats = {"impact_frame": 62}
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        assert F.frame_metrics_as_seconds(feats, bad) == {}


def test_conversion_does_not_touch_the_features_dict():
    """`features`가 그대로여야 판정 입력이 같고, 기존 평가와 비교가 끊기지 않는다."""
    feats = extract_features(build_sequence())
    before = dict(feats)

    F.frame_metrics_as_seconds(feats, 30.0)

    assert feats == before
    # 시간 값이 측정 이름공간으로 새어 들어가지 않았다.
    assert not any(k.endswith("_seconds") for k in feats)
