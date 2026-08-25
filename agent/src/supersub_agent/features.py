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
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16

# 관절 체인 (몸통쪽, 각도를 잴 관절, 말단). 위상 분할은 가운데 관절의 신전
# 각속도가 최대인 프레임을 임팩트로 삼는다 — 다리든 팔이든 구조가 같다.
Chain = tuple[int, int, int]
LIMB_CHAINS: dict[str, dict[str, Chain]] = {
    "leg": {
        "left": (L_HIP, L_KNEE, L_ANKLE),
        "right": (R_HIP, R_KNEE, R_ANKLE),
    },
    "arm": {
        "left": (L_SHOULDER, L_ELBOW, L_WRIST),
        "right": (R_SHOULDER, R_ELBOW, R_WRIST),
    },
}
LIMB_NAMES = {"leg": "하반신", "arm": "상반신"}

# 임팩트를 어느 사건으로 정의할지. 루브릭의 kinematics.impact_event가 고른다.
#
#   extension_peak — 스윙 관절의 신전 각속도가 최대인 프레임.
#       채찍처럼 말단을 던지는 동작. 축구 슈팅, 농구 점프슛, 배구 스파이크,
#       테니스 서브, 야구 투구가 여기 속한다.
#   distal_apex    — 스윙 체인 말단(손/발)이 가장 높이 올라간 프레임.
#       **들어올려 놓는** 동작. 농구 레이업이 대표적이다 — 팔꿈치를 채지 않고
#       공을 림까지 들고 가므로 신전 각속도 피크가 릴리스가 아니라 팔을 들기
#       시작하는 순간에 잡힌다(레이업 실클립에서 6프레임 vs 실제 21프레임).
IMPACT_EVENTS = ("extension_peak", "distal_apex")

MIN_CONFIDENCE = 0.3

# 사지별 최소 신뢰도. **손목은 가장 어려운 관절이라 기준이 달라야 한다.**
#
# 농구 점프슛 클립 실측: 0.3에서는 팔 유효 프레임이 96%로 통과하는데 팔꿈치
# 각도가 프레임마다 25도↔178도로 튄다 — 손목이 0.28~0.37로 잡힌 프레임이
# 그대로 섞여서다. 0.6으로 올리면 유효 73%로 줄지만 시계열이 매끄러워진다.
# 다리는 0.3에서도 안정적이라 그대로 둔다.
LIMB_MIN_CONFIDENCE = {"leg": 0.3, "arm": 0.6}

# 도구가 검출된 영상에서만 나오는 지표. 이 모듈이 산출할 수 있다는 선언이며,
# verify_rubric_coverage가 이 목록만 면제한다 (루브릭 오타는 계속 걸린다).
TOOL_DEPENDENT_METRICS = frozenset({"plant_foot_to_ball_offset"})

# 해당 사지 키포인트 신뢰도가 낮으면 빠지는 지표. 도구 지표와 같은 규약으로
# verify_rubric_coverage가 면제하고, 그 지표를 쓰는 항목은 판정에서 제외된다.
LIMB_DEPENDENT_METRICS = frozenset({
    "swing_elbow_angle_at_impact",
    "support_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg",
})


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


def normalization_params(kps: np.ndarray) -> tuple[np.ndarray, float]:
    """(프레임별 골반 중심, 어깨너비 스케일)을 돌려준다.

    키포인트와 도구 궤적에 **같은 변환**을 적용해야 둘 사이 거리를 잴 수 있다.
    스케일은 프레임마다가 아니라 전체 중앙값 하나를 쓴다 — 프레임별로 나누면
    추정 흔들림이 그대로 거리 지표에 실린다.
    """
    xy = kps[:, :, :2].astype(np.float64)
    hip_center = (xy[:, L_HIP] + xy[:, R_HIP]) / 2.0
    shoulder_width = np.linalg.norm(xy[:, L_SHOULDER] - xy[:, R_SHOULDER], axis=1)

    scale = np.median(shoulder_width[shoulder_width > 1e-6])
    if not np.isfinite(scale) or scale < 1e-6:
        raise InsufficientQuality("어깨 너비를 측정할 수 없어 정규화 불가")

    return hip_center, float(scale)


def normalize(kps: np.ndarray) -> np.ndarray:
    """어깨 너비로 스케일을 맞추고 골반 중심을 원점으로 옮긴다.

    이 단계를 생략하면 촬영 거리에 따라 같은 자세의 수치가 달라진다.
    각도 지표만 쓸 때는 영향이 없지만, 거리·낙차 지표에는 필수다.
    """
    hip_center, scale = normalization_params(kps)
    out = kps.copy().astype(np.float64)
    out[:, :, :2] = (out[:, :, :2] - hip_center[:, None, :]) / scale
    return out


def normalize_track(track: np.ndarray, kps: np.ndarray) -> np.ndarray:
    """도구 궤적 (T, 3)에 키포인트와 같은 정규화를 적용한다.

    신뢰도 열은 건드리지 않는다. 미검출 프레임(신뢰도 0)의 좌표는 의미가 없으므로
    변환하되 쓰는 쪽에서 신뢰도로 걸러야 한다.
    """
    if track.shape[0] != kps.shape[0]:
        raise ValueError(
            f"궤적 길이 {track.shape[0]}가 키포인트 길이 {kps.shape[0]}와 다름"
        )
    hip_center, scale = normalization_params(kps)
    out = track.astype(np.float64).copy()
    out[:, :2] = (out[:, :2] - hip_center) / scale
    return out


def valid_frames(kps: np.ndarray, limb: str = "leg") -> np.ndarray:
    """해당 사지 키포인트를 신뢰할 수 있는 프레임 마스크 (T,).

    사람이 검출되지 않은 프레임은 pose.py가 신뢰도 0으로 채우므로 여기서 걸린다.
    """
    joints = sorted({j for chain in LIMB_CHAINS[limb].values() for j in chain})
    threshold = LIMB_MIN_CONFIDENCE[limb]
    return (kps[:, joints, 2] >= threshold).all(axis=1)


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


def _apex_frame(height: np.ndarray, usable: np.ndarray) -> int:
    """유효 구간 안에서 말단 관절이 가장 높이 올라간 프레임.

    좌표계의 y축은 아래로 증가하므로 **최소값**이 최고점이다.
    _peak_frame과 같은 이유로 후보를 유효 프레임에 한정한다 — 미검출 프레임은
    좌표가 (0,0)이라 정규화 후 골반 위쪽으로 튀어 항상 최고점으로 잡힌다.
    """
    candidates = usable & np.isfinite(height)
    if not candidates.any():
        raise InsufficientQuality("말단 관절 높이를 산출할 수 있는 프레임이 없다.")
    return int(np.argmin(np.where(candidates, height, np.inf)))


def check_quality(
    kps: np.ndarray, min_valid_ratio: float = 0.7, limb: str = "leg"
) -> float:
    """해당 사지 키포인트의 유효 프레임 비율을 반환한다."""
    ratio = float(valid_frames(kps, limb).mean())
    if ratio < min_valid_ratio:
        raise InsufficientQuality(
            f"{LIMB_NAMES[limb]} 키포인트 유효 프레임 비율 {ratio:.0%} < "
            f"기준 {min_valid_ratio:.0%}. 재촬영이 필요하다."
        )
    return ratio


def identify_limb(kps: np.ndarray, limb: str = "leg") -> tuple[Chain, Chain]:
    """(스윙 측, 지지 측) 관절 체인을 판별한다.

    스윙 측은 말단 관절(발목/손목)이 더 크게 움직인 쪽이다. 축구에서는 차는
    다리, 농구에서는 슛하는 팔이 여기에 해당한다.

    실클립에서 공 궤적이 이 판별을 뒷받침했다 — 디딤발로 지목된 쪽이 공 옆에
    붙어 있고(간격 일정), 차는 발로 지목된 쪽이 공으로 빠르게 접근했다.
    """
    chains = LIMB_CHAINS[limb]
    xy = kps[:, :, :2]

    def travel(chain: Chain) -> float:
        distal = chain[2]
        return float(np.linalg.norm(np.diff(xy[:, distal], axis=0), axis=1).sum())

    left, right = chains["left"], chains["right"]
    if travel(left) >= travel(right):
        return left, right
    return right, left


def chain_series(kps: np.ndarray, chain: Chain) -> np.ndarray:
    """체인 가운데 관절을 꼭짓점으로 한 각도 시계열."""
    proximal, joint, distal = chain
    xy = kps[:, :, :2]
    return np.array(
        [joint_angle(f[proximal], f[joint], f[distal]) for f in xy]
    )


def identify_legs(kps: np.ndarray) -> tuple[int, int]:
    """(차는 다리, 디딤발)의 무릎 인덱스. identify_limb의 다리 전용 래퍼."""
    swing, support = identify_limb(kps, "leg")
    return swing[1], support[1]


def _knee_series(kps: np.ndarray, knee_idx: int) -> np.ndarray:
    """무릎 각도 시계열. chain_series의 다리 전용 래퍼."""
    side = "left" if knee_idx == L_KNEE else "right"
    return chain_series(kps, LIMB_CHAINS["leg"][side])


def segment_phases(
    kps: np.ndarray,
    swing: int | Chain,
    limb: str = "leg",
    event: str = "extension_peak",
) -> Phases:
    """준비·임팩트·마무리 구간을 나눈다.

    임팩트의 정의는 **루브릭이 고른다** (IMPACT_EVENTS 참고).

      extension_peak — 스윙 측 관절의 신전 각속도가 최대인 지점. 다리(무릎)든
        팔(팔꿈치)든 같은 규칙이다 — 축구 슈팅의 임팩트와 농구 점프슛의 릴리스는
        구조가 같은 사건이다.
      distal_apex — 스윙 체인 말단이 최고점에 이른 지점. 채찍질이 없는 동작에
        쓴다. 레이업 실클립에서 extension_peak은 팔을 들기 시작하는 6프레임을
        잡았고, 실제 릴리스는 손이 최고점인 21프레임이었다.

    어느 쪽이든 언어 모델을 쓰지 않는다 — 재현성이 필요한 구간이다.

    swing은 관절 체인이거나, 하위 호환을 위한 무릎 인덱스 하나다.
    """
    if event not in IMPACT_EVENTS:
        raise ValueError(f"impact_event는 {list(IMPACT_EVENTS)} 중 하나여야 한다: {event!r}")
    if isinstance(swing, int):   # 다리 전용 옛 호출 형태
        swing = LIMB_CHAINS["leg"]["left" if swing == L_KNEE else "right"]

    series = chain_series(kps, swing)
    usable = valid_frames(kps, limb) & np.isfinite(series)
    if event == "extension_peak":
        impact = _peak_frame(np.gradient(series), usable)
    else:
        impact = _apex_frame(kps[:, swing[2], 1], usable)

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


def _ball_at(ball: np.ndarray, t: int, window: int = 2) -> np.ndarray | None:
    """t 프레임의 공 위치. 그 프레임이 미검출이면 ±window에서 가장 가까운 검출을 쓴다.

    접촉 순간은 모션 블러로 검출이 빠지기 쉽다 — 실클립에서 임팩트 다음 프레임이
    정확히 그렇게 비었다. 한두 프레임 옆의 위치로 대체하는 편이 지표를 통째로
    버리는 것보다 낫다.
    """
    for offset in range(window + 1):
        for t2 in ({t - offset, t + offset} if offset else {t}):
            if 0 <= t2 < len(ball) and ball[t2, 2] > 0:
                return ball[t2, :2]
    return None


def extract_features(
    kps: np.ndarray,
    objects: dict[str, np.ndarray] | None = None,
    impact_limb: str = "leg",
    impact_event: str = "extension_peak",
) -> dict[str, float | int]:
    """루브릭이 요구하는 지표를 모두 산출한다.

    반환 키는 루브릭의 measured_by와 일치한다.

    objects는 pose.PoseResult.objects — 도구가 검출되지 않은 영상에서는 도구
    기반 지표가 빠진다. 그 지표를 쓰는 채점 항목은 판정에서 제외된다
    (scoring.Rubric.applicable_criteria).

    impact_limb은 임팩트를 정의할 사지다 (루브릭의 kinematics.impact_limb).
    축구 슈팅은 다리, 농구 슛·테니스 스트로크는 팔이다. 어느 쪽이든 다리·팔
    지표를 **둘 다** 산출하고, 루브릭이 measured_by로 쓸 것을 고른다.

    impact_event는 임팩트로 삼을 사건이다 (루브릭의 kinematics.impact_event).
    채찍질하는 동작은 extension_peak, 들어올려 놓는 동작은 distal_apex다.
    """
    if impact_limb not in LIMB_CHAINS:
        raise ValueError(
            f"impact_limb은 {sorted(LIMB_CHAINS)} 중 하나여야 한다: {impact_limb!r}"
        )

    check_quality(kps, limb=impact_limb)
    norm = normalize(kps)
    swing_knee, plant_knee = identify_legs(norm)
    swing_chain, support_chain = identify_limb(norm, impact_limb)
    phases = segment_phases(norm, swing_chain, impact_limb, impact_event)
    t = phases.impact

    xy = norm[:, :, :2]
    swing_hip = L_HIP if swing_knee == L_KNEE else R_HIP
    swing_ankle = L_ANKLE if swing_knee == L_KNEE else R_ANKLE
    plant_ankle = L_ANKLE if plant_knee == L_KNEE else R_ANKLE

    swing_series = _knee_series(norm, swing_knee)
    plant_series = _knee_series(norm, plant_knee)

    # 상체 기울기 — 골반중심→어깨중심 벡터가 수직에서 앞으로 기운 각도.
    shoulder_c = (xy[t, L_SHOULDER] + xy[t, R_SHOULDER]) / 2.0
    hip_c = (xy[t, L_HIP] + xy[t, R_HIP]) / 2.0
    trunk = shoulder_c - hip_c
    trunk_lean = float(np.degrees(np.arctan2(trunk[0], -trunk[1])))

    # 골반 회전 — 좌우 골반 벡터 방향각의 백스윙~임팩트 구간 변화폭.
    #
    # **각도를 언랩하고 유효 프레임만 본다.** arctan2는 -180~180을 돌려주므로
    # 골반이 그 경계에 걸치면 ptp가 360에 가까운 값을 낸다 — 농구 클립에서
    # 실제 회전 12.7도가 359.0도로 나왔다. 축구 클립도 방향각이 -172~178이라
    # 경계 위에 있었고, 값이 멀쩡했던 것은 구간이 우연히 경계를 안 넘어서다.
    # 미검출 프레임은 골반 벡터가 (0,0)이라 각도가 0으로 튀므로 함께 제외한다.
    leg_usable = valid_frames(norm, "leg")
    hip_vec = xy[:, L_HIP] - xy[:, R_HIP]
    hip_angle = np.arctan2(hip_vec[:, 1], hip_vec[:, 0])
    tb_start, tb_end = phases.takeback
    span_idx = [f for f in range(tb_start, tb_end + 1) if leg_usable[f]]
    if len(span_idx) >= 2:
        unwrapped = np.degrees(np.unwrap(hip_angle[span_idx]))
        hip_rotation_range = float(np.ptp(unwrapped))
    else:
        hip_rotation_range = 0.0

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

    features: dict[str, float | int] = {
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

    # 팔 지표 — 다리와 구조가 같다. 임팩트를 다리로 정의한 종목에서도 함께
    # 산출한다(상체 자세를 근거로 삼는 항목이 있을 수 있다). 신뢰도가 낮으면
    # NaN이 되므로 판정 근거로 쓰기 전에 걸러야 한다.
    arm_swing, arm_support = identify_limb(norm, "arm")
    arm_swing_series = chain_series(norm, arm_swing)
    arm_support_series = chain_series(norm, arm_support)
    arm_usable = valid_frames(norm, "arm") & np.isfinite(arm_swing_series)
    if arm_usable[t]:
        features["swing_elbow_angle_at_impact"] = round(float(arm_swing_series[t]), 1)
        if np.isfinite(arm_support_series[t]):
            features["support_elbow_angle_at_impact"] = round(
                float(arm_support_series[t]), 1
            )

        # 스윙 팔 어깨 굴곡 — 임팩트 후 얼마나 더 진행됐는가 (팔로스루).
        # **유효 프레임만** 본다. 신뢰도 낮은 프레임을 섞으면 관절이 튀면서
        # 100도가 넘는 가짜 굴곡이 나온다(실클립에서 109.2도로 확인).
        shoulder_idx, elbow_idx = arm_swing[0], arm_swing[1]
        hip_idx = L_HIP if shoulder_idx == L_SHOULDER else R_HIP

        def shoulder_flexion(frame: int) -> float:
            return joint_angle(
                xy[frame, hip_idx], xy[frame, shoulder_idx], xy[frame, elbow_idx]
            )

        window = [f for f in range(ft_start, ft_end + 1) if arm_usable[f]]
        after = [shoulder_flexion(f) for f in window]
        after = [a for a in after if np.isfinite(a)]
        if after:
            at_impact = shoulder_flexion(t)
            if np.isfinite(at_impact):
                features["swing_shoulder_flexion_after_impact_deg"] = round(
                    float(max(after) - at_impact), 1
                )

    # 도구 기반 지표 — 공이 검출된 영상에서만 나온다.
    ball = (objects or {}).get("sports_ball")
    if ball is not None:
        ball_at_impact = _ball_at(normalize_track(ball, kps), t)
        if ball_at_impact is not None:
            # **수평 성분만** 쓴다. 유클리드 거리에는 공 반지름만큼의 수직 오프셋이
            # 섞이는데, 실측하면 그 수직 성분이 공 반지름과 부호조차 맞지 않는다
            # (실클립에서 Δy=-0.30, 발목이 공 중심보다 위로 나옴). 원근과 검출
            # 박스 중심 오차가 겹친 결과라 판정 근거로 쓸 수 없다.
            #
            # 측면 촬영에서 이 값은 **앞뒤** 배치로, 정면·후면 촬영에서는 좌우로
            # 읽힌다. 촬영 축을 루브릭이 전제하므로 지도자 검수 때 함께 확정한다.
            offset_x = abs(float(xy[t, plant_ankle][0] - ball_at_impact[0]))
            features["plant_foot_to_ball_offset"] = round(offset_x, 2)

    return features


def verify_rubric_coverage(rubric, features: dict) -> None:
    """루브릭이 요구하는 지표를 파이프라인이 모두 산출했는지 검사한다.

    측정값에 없는 지표를 근거로 쓰게 두면 모델이 수치를 지어낸다.

    도구·사지 조건에 따라 빠질 수 있는 지표는 이번 영상에 없어도 통과시킨다 —
    다만 **이 모듈이 산출할 수 있다고 선언한 것**만 면제한다. 루브릭에 오타가
    나면 선언 목록에 없으므로 여전히 걸린다.
    """
    optional = TOOL_DEPENDENT_METRICS | LIMB_DEPENDENT_METRICS
    missing = rubric.required_metrics() - features.keys() - optional
    if missing:
        raise ValueError(
            f"루브릭이 요구하지만 파이프라인이 산출하지 않은 지표: {sorted(missing)}"
        )
