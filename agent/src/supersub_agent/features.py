"""포즈 키포인트 시계열 → 채점 지표.

이 모듈이 산출하는 지표 이름은 루브릭의 measured_by와 **정확히 일치해야 한다.**
불일치하면 판정 단계에서 근거 지표를 찾지 못한다 (verify_rubric_coverage로 검사).

입력은 COCO-17 포맷 키포인트 (ViTPose 출력): (T, 17, 3) — x, y, confidence.
좌표계는 이미지 픽셀 기준이며, y축은 아래로 증가한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# COCO-17 인덱스
NOSE = 0
L_SHOULDER, R_SHOULDER = 5, 6
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16

MIN_CONFIDENCE = 0.3


class InsufficientQuality(ValueError):
    """키포인트 품질이 낮아 지표를 산출할 수 없는 경우.

    낮은 품질의 입력으로 낸 점수는 근거가 없으므로 제공하지 않는다.
    """


@dataclass(frozen=True)
class Phases:
    takeback: tuple[int, int]
    impact: int
    follow_through: tuple[int, int]


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """b를 꼭짓점으로 하는 세 점의 각도 (도)."""
    ba, bc = a - b, c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-8:
        return float("nan")
    cos = float(np.dot(ba, bc) / denom)
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def normalize(kps: np.ndarray) -> np.ndarray:
    """어깨 너비로 스케일을 맞추고 골반 중심을 원점으로 옮긴다.

    이 단계를 생략하면 촬영 거리에 따라 같은 자세의 수치가 달라진다.
    각도 지표만 쓸 때는 영향이 없지만, 거리·낙차 지표에는 필수다.
    """
    xy = kps[:, :, :2].astype(np.float64)
    hip_center = (xy[:, L_HIP] + xy[:, R_HIP]) / 2.0
    shoulder_width = np.linalg.norm(xy[:, L_SHOULDER] - xy[:, R_SHOULDER], axis=1)

    scale = np.median(shoulder_width[shoulder_width > 1e-6])
    if not np.isfinite(scale) or scale < 1e-6:
        raise InsufficientQuality("어깨 너비를 측정할 수 없어 정규화 불가")

    out = kps.copy().astype(np.float64)
    out[:, :, :2] = (xy - hip_center[:, None, :]) / scale
    return out


def valid_frames(kps: np.ndarray) -> np.ndarray:
    """하반신 키포인트를 신뢰할 수 있는 프레임 마스크 (T,).

    사람이 검출되지 않은 프레임은 pose.py가 신뢰도 0으로 채우므로 여기서 걸린다.
    """
    lower_body = [L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE]
    return (kps[:, lower_body, 2] >= MIN_CONFIDENCE).all(axis=1)


def _peak_frame(velocity: np.ndarray, usable: np.ndarray) -> int:
    """유효 구간 안에서 각속도가 최대인 프레임을 찾는다.

    검출 실패 프레임은 세 점이 모두 (0,0)이라 joint_angle이 NaN을 낸다.
    np.argmax는 NaN을 최대값으로 취급하므로 후보를 유효 프레임으로 한정하지
    않으면 임팩트가 항상 그 프레임으로 잡힌다. 실클립에서 실제로 발생했다.
    """
    candidates = usable & np.isfinite(velocity)
    if not candidates.any():
        raise InsufficientQuality("각속도를 산출할 수 있는 프레임이 없다.")
    return int(np.argmax(np.where(candidates, velocity, -np.inf)))


def check_quality(kps: np.ndarray, min_valid_ratio: float = 0.7) -> float:
    """하반신 키포인트의 유효 프레임 비율을 반환한다."""
    ratio = float(valid_frames(kps).mean())
    if ratio < min_valid_ratio:
        raise InsufficientQuality(
            f"하반신 키포인트 유효 프레임 비율 {ratio:.0%} < 기준 {min_valid_ratio:.0%}. "
            "재촬영이 필요하다."
        )
    return ratio


def identify_legs(kps: np.ndarray) -> tuple[int, int]:
    """(차는 다리, 디딤발) 측을 판별해 각각 knee 인덱스로 반환한다.

    차는 다리는 스윙 구간에서 발목이 더 크게 움직인다.
    """
    xy = kps[:, :, :2]
    l_travel = float(np.linalg.norm(np.diff(xy[:, L_ANKLE], axis=0), axis=1).sum())
    r_travel = float(np.linalg.norm(np.diff(xy[:, R_ANKLE], axis=0), axis=1).sum())
    if l_travel >= r_travel:
        return L_KNEE, R_KNEE
    return R_KNEE, L_KNEE


def _knee_series(kps: np.ndarray, knee_idx: int) -> np.ndarray:
    hip_idx = L_HIP if knee_idx == L_KNEE else R_HIP
    ankle_idx = L_ANKLE if knee_idx == L_KNEE else R_ANKLE
    xy = kps[:, :, :2]
    return np.array(
        [joint_angle(f[hip_idx], f[knee_idx], f[ankle_idx]) for f in xy]
    )


def segment_phases(kps: np.ndarray, swing_knee: int) -> Phases:
    """각속도 극값으로 준비·임팩트·마무리 구간을 나눈다.

    임팩트는 차는 다리 무릎 신전 각속도가 최대인 지점으로 정의한다.
    언어 모델을 쓰지 않는다 — 재현성이 필요한 구간이다.
    """
    knee = _knee_series(kps, swing_knee)
    velocity = np.gradient(knee)
    usable = valid_frames(kps) & np.isfinite(knee)
    impact = _peak_frame(velocity, usable)

    # 구간 분할은 검출된 범위 안에서만 성립한다. 앞뒤로 검출 실패 구간이
    # 붙어 있을 수 있으므로 클립 전체가 아니라 유효 구간의 경계와 비교한다.
    first = int(np.argmax(usable))
    last = int(len(usable) - 1 - np.argmax(usable[::-1]))

    if impact - first < 2 or last - impact < 2:
        raise InsufficientQuality(
            f"임팩트 추정 프레임({impact})이 분석 가능 구간({first}~{last}) 경계에 있음. "
            "동작 전후가 잘린 영상으로 보인다."
        )

    return Phases(
        takeback=(first, impact),
        impact=impact,
        follow_through=(impact, last),
    )


def extract_features(kps: np.ndarray) -> dict[str, float | int]:
    """루브릭이 요구하는 지표를 모두 산출한다.

    반환 키는 football_instep_shot.yaml의 measured_by와 일치한다.
    """
    check_quality(kps)
    norm = normalize(kps)
    swing_knee, plant_knee = identify_legs(norm)
    phases = segment_phases(norm, swing_knee)
    t = phases.impact

    xy = norm[:, :, :2]
    swing_hip = L_HIP if swing_knee == L_KNEE else R_HIP
    swing_ankle = L_ANKLE if swing_knee == L_KNEE else R_ANKLE

    swing_series = _knee_series(norm, swing_knee)
    plant_series = _knee_series(norm, plant_knee)

    # 상체 기울기 — 골반중심→어깨중심 벡터가 수직에서 앞으로 기운 각도.
    shoulder_c = (xy[t, L_SHOULDER] + xy[t, R_SHOULDER]) / 2.0
    hip_c = (xy[t, L_HIP] + xy[t, R_HIP]) / 2.0
    trunk = shoulder_c - hip_c
    trunk_lean = float(np.degrees(np.arctan2(trunk[0], -trunk[1])))

    # 골반 회전 — 좌우 골반 벡터 방향각의 백스윙~임팩트 구간 변화폭.
    hip_vec = xy[:, L_HIP] - xy[:, R_HIP]
    hip_angle = np.degrees(np.arctan2(hip_vec[:, 1], hip_vec[:, 0]))
    tb_start, tb_end = phases.takeback
    hip_span = hip_angle[tb_start : tb_end + 1]
    hip_rotation_range = float(np.ptp(hip_span)) if hip_span.size else 0.0

    # 팔로스루 — 임팩트 후 차는 다리 고관절 굴곡이 얼마나 더 진행됐는가.
    def hip_flexion(frame: int) -> float:
        return joint_angle(xy[frame, L_SHOULDER if swing_hip == L_HIP else R_SHOULDER],
                           xy[frame, swing_hip],
                           xy[frame, swing_knee])

    ft_start, ft_end = phases.follow_through
    flexion_at_impact = hip_flexion(t)
    flexion_after = [hip_flexion(f) for f in range(ft_start, ft_end + 1)]
    max_additional = float(np.nanmax(flexion_after) - flexion_at_impact)

    # 스윙이 실제로 감속하기까지의 프레임 수.
    ankle_speed = np.linalg.norm(np.diff(xy[:, swing_ankle], axis=0), axis=1)
    post = ankle_speed[t:]
    threshold = float(post[0]) * 0.3 if post.size else 0.0
    decel = np.argmax(post < threshold) if (post < threshold).any() else len(post)

    return {
        "plant_knee_angle_at_impact": round(float(plant_series[t]), 1),
        "swing_knee_angle_at_impact": round(float(swing_series[t]), 1),
        # 각속도 피크와 임팩트의 시간차는 산출하지 않는다 — segment_phases가
        # 임팩트를 그 피크로 정의하므로 정의상 항상 0이고, 판정 근거로 넘기면
        # 모델이 0을 "가속 구간 확보 실패"로 읽는다.
        # 루브릭 deferred: swing_acceleration_timing 참고.
        "trunk_forward_lean_deg_at_impact": round(trunk_lean, 1),
        "hip_rotation_range_deg": round(hip_rotation_range, 1),
        "swing_hip_flexion_after_impact_deg": round(max_additional, 1),
        "follow_through_duration_frames": int(decel),
        "impact_frame": int(t),
    }


def verify_rubric_coverage(rubric, features: dict) -> None:
    """루브릭이 요구하는 지표를 파이프라인이 모두 산출했는지 검사한다.

    측정값에 없는 지표를 근거로 쓰게 두면 모델이 수치를 지어낸다.
    """
    missing = rubric.required_metrics() - features.keys()
    if missing:
        raise ValueError(
            f"루브릭이 요구하지만 파이프라인이 산출하지 않은 지표: {sorted(missing)}"
        )
