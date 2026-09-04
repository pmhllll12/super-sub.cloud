"""포즈 키포인트 시계열 → 채점 지표.

이 모듈이 산출하는 지표 이름은 루브릭의 measured_by와 **정확히 일치해야 한다.**
불일치하면 판정 단계에서 근거 지표를 찾지 못한다 (verify_rubric_coverage로 검사).

입력은 COCO-17 포맷 키포인트 (ViTPose 출력): (T, 17, 3) — x, y, confidence.
좌표계는 이미지 픽셀 기준이며, y축은 아래로 증가한다.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
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
#       채찍처럼 말단을 던지는 동작. 축구 슈팅, 농구 점프슛, 야구 투구가
#       여기 속한다.
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

# 품질 게이트가 요구할 관절 — 체인의 몸통쪽부터 몇 개인가 (check_quality).
#
#   arm 2 — 어깨·팔꿈치만 본다. 손목은 **프레임 단위로만** 반영한다(valid_frames).
#       손목은 가려지기 쉬운데(투구 와인드업의 글러브, 슛의 공) 팔 루브릭이
#       손목을 쓰는 곳은 팔꿈치각 하나뿐이다. 전 구간 70%를 요구하면 그 한
#       지표 때문에 나머지를 통째로 버린다. 실측: 손목을 필수에서 빼면 최종
#       산출이 야구 3,444클립에서 21.1%→70.8%, 농구 134클립에서 11.2%→39.6%로
#       늘고, 두 조건 모두 통과한 클립의 측정값은 100% 동일했다.
#   leg 3 — 발목까지 전부 요구한다. 무릎각이 joint_angle(엉덩이, 무릎, 발목)이라
#       발목이 빠지면 각도 자체가 NaN이 되고, 임팩트를 그 각도의 신전 각속도
#       피크로 정의하므로 임팩트마저 못 찾는다. 축구 17건에서 발목 신뢰도를
#       0으로 만들자 17/17 전부 실패했다 — 팔과 달리 여기서는 뺄 수 없다.
GATE_JOINTS = {"arm": 2, "leg": 3}

# 골반·어깨 축을 각도로 쓸 수 있는 최소 투영 길이 (어깨너비 = 1.0 기준).
#
# 몸통이 카메라를 향하면 좌우 두 점이 겹쳐 보여 축이 짧아지고, 그 각도는 작은
# 키포인트 오차에도 크게 흔들린다. 야구 투구 실클립에서 골반 축이 0.44로 줄어든
# 프레임이 분리각 81.2도를 냈다 — 축이 제대로 보이는 프레임에서는 49.9도였다.
MIN_AXIS_LENGTH = 0.6

# 지표별 물리적으로 가능한 범위. 벗어난 값은 등급이 아니라 **측정 실패**로 뺀다.
#
# 밴드를 양끝에서 닫아도(scoring._parse_bands) 그것만으로는 부족하다. 닫힌 밴드는
# 범위 밖 값을 0등급으로 떨어뜨리는데, 측정이 깨진 것을 "못한 것"으로 채점하는
# 셈이기 때문이다. 촬영 조건으로 선수를 감점하지 않는다는 원칙(도구 미검출 처리)이
# 여기에도 그대로 적용된다 — 잴 수 없었으면 그 항목을 빼고 나머지로 채점한다.
#
# 각도 지표의 상한 180은 기하학적 최대다(joint_angle은 arccos 기반이라 0~180).
# 나머지는 사람 몸에서 나올 수 있는 범위로 잡되, 실측 분포가 쌓이면 다시 본다.
PLAUSIBLE_RANGE: dict[str, tuple[float, float]] = {
    "plant_knee_angle_at_impact": (0.0, 180.0),
    "swing_knee_angle_at_impact": (0.0, 180.0),
    "swing_elbow_angle_at_impact": (0.0, 180.0),
    "support_elbow_angle_at_impact": (0.0, 180.0),
    # 상체가 앞뒤로 90도를 넘으면 뒤집힌 자세다 — 측정이 깨진 것으로 본다.
    "trunk_forward_lean_deg_at_impact": (-90.0, 90.0),
    # 준비~임팩트 구간의 골반 축 회전. 축 기준(mod 180)이라 180이 상한이다.
    "hip_rotation_range_deg": (0.0, 180.0),
    # 두 축의 차이를 -90~90으로 접은 절대값.
    "hip_shoulder_separation_deg": (0.0, 90.0),
    "swing_hip_flexion_after_impact_deg": (0.0, 180.0),
    "swing_shoulder_flexion_after_impact_deg": (0.0, 180.0),
}

# 도구가 검출된 영상에서만 나오는 지표. 이 모듈이 산출할 수 있다는 선언이며,
# verify_rubric_coverage가 이 목록만 면제한다 (루브릭 오타는 계속 걸린다).
TOOL_DEPENDENT_METRICS = frozenset({"plant_foot_to_ball_offset"})

# 해당 사지 키포인트 신뢰도가 낮으면 빠지는 지표. 도구 지표와 같은 규약으로
# verify_rubric_coverage가 면제하고, 그 지표를 쓰는 항목은 판정에서 제외된다.
LIMB_DEPENDENT_METRICS = frozenset({
    "swing_elbow_angle_at_impact",
    "support_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg",
    # 어깨·골반 네 점이 모두 잡힌 프레임에서만 나온다.
    "hip_shoulder_separation_deg",
})

# --- 프레임 단위 지표 (미결 7번 E-3) ---------------------------------------
#
# **프레임 수는 그 자체로 뜻이 없다.** 62프레임이 몇 초인지는 어느 격자에서
# 뽑았는지에 달려 있고, 그 격자는 소스 fps마다 다르다 — `read_frames`가
# `step = max(1, round(src_fps / target_fps))`로 솎으므로 25fps 소스에 target 15를
# 주면 실효 12.5fps다. 목표값을 실효값인 양 읽으면 **20% 어긋난다**(pose.read_frames).
#
# 그래서 프레임 단위 값을 내보내는 자리에는 **물리 시간을 함께** 붙인다.
# 아래 두 목록이 "무엇이 프레임 단위인가"의 선언이고,
# `test_features.py`가 새 지표가 여기 빠지면 걸리게 지킨다.
#
# 🔴 **`features` 딕셔너리 자체는 바꾸지 않는다.** 시간은 결과 봉투의 별도
# 블록(`timebase`)으로 나간다 — `features`는 루브릭·판정·적재가 읽는 측정
# 이름공간이고, 격자 정보는 선수에 대한 측정이 아니다. 여기에 키를 더하면
# 판정 입력이 달라져 기존 평가(B-2~B-6)와 비교가 끊긴다.

# 값이 **샘플링된 프레임 인덱스**인 지표. 시각으로 읽으려면 나눈다.
FRAME_INDEX_METRICS = frozenset({"impact_frame"})

# 값이 **프레임 개수(지속시간)**인 지표. 초로 읽으려면 같은 수로 나눈다.
FRAME_DURATION_METRICS = frozenset({"follow_through_duration_frames"})


def frame_metrics_as_seconds(
    features: dict, sampled_fps: float
) -> dict[str, float]:
    """프레임 단위 지표를 초로 환산한다. **원본 `features`를 건드리지 않는다.**

    인덱스든 개수든 나누는 수는 같다(`sampled_fps`). 둘을 목록으로 갈라 둔 것은
    뜻이 달라서다 — 인덱스는 *언제*이고 개수는 *얼마나 오래*다. 읽는 쪽이
    그걸 구분해야 "임팩트 2.07초"와 "팔로스루 0.27초"를 섞지 않는다.

    `sampled_fps`가 0 이하이거나 유한하지 않으면 **빈 dict를 돌려준다** —
    모르는 격자에서 시간을 지어내지 않는다. 그것이 이 결함의 원인이었다.
    """
    if not sampled_fps or not math.isfinite(sampled_fps) or sampled_fps <= 0:
        return {}
    out: dict[str, float] = {}
    for key in FRAME_INDEX_METRICS | FRAME_DURATION_METRICS:
        value = features.get(key)
        if value is None:
            continue
        out[key] = round(float(value) / sampled_fps, 3)
    return out


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


def _axis_deg(vec: np.ndarray) -> np.ndarray:
    """방향 벡터를 **축 각도**(0~180)로 바꾼다.

    골반·어깨처럼 좌우 두 점을 잇는 선은 방향이 아니라 축이다 — 좌우 라벨이
    뒤바뀌어도 같은 자세이므로, 벡터 각도로 다루면 라벨 스왑이 180도 회전으로
    잘못 읽힌다 (야구 투구 실클립에서 실제로 발생).
    """
    return np.degrees(np.arctan2(vec[:, 1], vec[:, 0])) % 180.0


def valid_frames(
    kps: np.ndarray, limb: str = "leg", chain: Sequence[int] | None = None
) -> np.ndarray:
    """해당 사지 키포인트를 신뢰할 수 있는 프레임 마스크 (T,).

    사람이 검출되지 않은 프레임은 pose.py가 신뢰도 0으로 채우므로 여기서 걸린다.

    chain을 주면 그 관절들만 본다. 좌우 양쪽을 모두 요구하면 한쪽이 가려진
    동작이 통째로 막히기 때문이다 (check_quality 참고). 체인 전체가 아니라
    **앞 몇 관절만** 넘어오기도 한다 — 품질 게이트가 그렇게 쓴다(GATE_JOINTS).
    """
    if chain is None:
        joints = sorted({j for c in LIMB_CHAINS[limb].values() for j in c})
    else:
        joints = sorted(set(chain))
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
    kps: np.ndarray,
    min_valid_ratio: float = 0.7,
    limb: str = "leg",
    side: str = "auto",
) -> float:
    """**스윙 측** 사지 키포인트의 유효 프레임 비율을 반환한다.

    좌우 양쪽을 함께 요구하지 않는다. 야구 투구 실클립(2160×3840 25fps, 투구
    구간 3.6초)에서 던지는 팔은 98%인데 글러브 팔이 50%라 전체로는 48%가 되어
    반려됐다 — 와인드업에서 글러브가 반대쪽 손을 덮기 때문이며, 촬영을 다시
    해도 사라지지 않는 가림이다. 투구 루브릭이 근거로 쓰는 지표는 모두 던지는
    팔에서 나오므로, 쓰지도 않는 팔 때문에 98%짜리 입력을 버리게 된다.

    스윙 측에서도 **체인 전체를 요구하지 않는다.** 사지마다 몇 관절을 볼지는
    GATE_JOINTS가 정한다 — 팔은 어깨·팔꿈치까지, 다리는 발목까지다. 팔에서
    손목을 뺀 것은 그것이 팔꿈치각 하나에만 쓰이기 때문이고, 다리에서 발목을
    남긴 것은 그것이 무릎각의 구성 요소라 빠지면 임팩트조차 못 찾기 때문이다.

    게이트에서 빠진 관절(팔의 손목)은 **지표 단위로** 걸러진다 — 프레임별
    valid_frames 마스크가 그대로 남아 있고, 산출되지 않은 지표는
    LIMB_DEPENDENT_METRICS 규약에 따라 해당 채점 항목이 판정에서 제외되며
    가중치가 재정규화된다. 지지 측 지표도 같은 경로로 처리된다.
    """
    # 스윙 측 판별은 **정규화 후** 좌표로 한다. 원좌표에서는 몸 전체의 이동이
    # 좌우 이동량에 함께 실려 반대쪽을 스윙으로 집는다.
    swing, _ = identify_limb(normalize(kps), limb, side)
    gate_chain = swing[:GATE_JOINTS[limb]]
    ratio = float(valid_frames(kps, limb, gate_chain).mean())
    if ratio < min_valid_ratio:
        raise InsufficientQuality(
            f"{LIMB_NAMES[limb]} 스윙 측 키포인트({len(gate_chain)}개 관절) "
            f"유효 프레임 비율 {ratio:.0%} < 기준 {min_valid_ratio:.0%}. "
            "재촬영이 필요하다."
        )
    return ratio


def identify_limb(
    kps: np.ndarray, limb: str = "leg", side: str = "auto"
) -> tuple[Chain, Chain]:
    """(스윙 측, 지지 측) 관절 체인을 판별한다.

    스윙 측은 말단 관절(발목/손목)이 더 크게 움직인 쪽이다. 축구에서는 차는
    다리, 농구에서는 슛하는 팔이 여기에 해당한다.

    실클립에서 공 궤적이 이 판별을 뒷받침했다 — 디딤발로 지목된 쪽이 공 옆에
    붙어 있고(간격 일정), 차는 발로 지목된 쪽이 공으로 빠르게 접근했다.

    **팔 종목에서는 이 자동 판별이 약하다.** 실클립 두 건으로 확인한 것 —
    현재 동작점(target 30 = 실효 25fps·23.98fps), 괄호는 옛 target 15 값이다:

      - 야구 투구: 던지는 왼팔 23.5 대 글러브 오른팔 33.1로 **뒤집힌다**
        (18.2 대 27.6). 샘플링을 두 배로 올려도 뒤집힘은 남는다 — 마진이
        34%에서 29%로 줄었을 뿐이다.
      - 농구 레이업: 18.7 대 17.1로 맞는 쪽을 고른다 (16.30 대 16.09).
        마진이 1.3%에서 8.7%로 벌어졌지만 여전히 근거라고 하기엔 얇다.

    **뒤집힘의 원인은 밝혀지지 않았다.** 옛 주석은 "12.5fps에서 릴리스가 두
    프레임 안에 끝나 던지는 팔의 경로가 짧고 글러브 팔은 내내 크게 돈다"고
    적었는데, 실측은 반대다 — 12.5fps에서 경로가 가장 긴 두 프레임이 차지하는
    비중은 던지는 팔 21%, 글러브 팔 32%로 **글러브 팔 쪽이 더 몰려 있다.**
    샘플링을 두 배로 올렸을 때 travel이 던지는 팔에서 조금 더 늘긴 하지만
    (×1.29 대 ×1.20) 29% 격차를 메울 크기가 아니다. 신뢰도도 "0.3~0.6"이
    아니라 글러브 팔 체인 중앙값 0.77이다(세 관절이 모두 0.6 이상인 프레임은
    49%). 재계산은 eval/pending6_side/가 GPU 없이 한다.

    본 프레임만 세거나 관측 비율로 할인하거나 손 높이로 바꿔 봐도, 세 클립을
    동시에 맞히는 통계는 찾지 못했다(야구를 맞히면 레이업이 뒤집힌다). 프레임
    수로 정규화하는 것도 처방이 아니다 — 평가셋 39클립에서 갈림이 오히려
    늘었다(미결 7번). 그래서
    자동 판별은 그대로 두고 **side로 지정할 수 있게** 열어 둔다 — 던지는 팔·차는
    발은 업로드하는 사람이 아는 값이고, 틀리면 조용히 반대쪽을 채점하게 된다.
    """
    chains = LIMB_CHAINS[limb]
    if side in ("left", "right"):
        other = "right" if side == "left" else "left"
        return chains[side], chains[other]
    if side != "auto":
        raise ValueError(f"side는 auto·left·right 중 하나여야 한다: {side!r}")

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


def identify_legs(kps: np.ndarray, side: str = "auto") -> tuple[int, int]:
    """(차는 다리, 디딤발)의 무릎 인덱스. identify_limb의 다리 전용 래퍼."""
    swing, support = identify_limb(kps, "leg", side)
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
    # 임팩트는 스윙 측 관절로 정의한다. 반대쪽이 가려진 프레임까지 후보에서
    # 빼면 임팩트가 실제 지점 밖으로 밀린다 (야구 투구 실클립).
    usable = valid_frames(kps, limb, swing) & np.isfinite(series)
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
    swing_side: str = "auto",
) -> dict[str, float | int]:
    """루브릭이 요구하는 지표를 모두 산출한다.

    반환 키는 루브릭의 measured_by와 일치한다.

    objects는 pose.PoseResult.objects — 도구가 검출되지 않은 영상에서는 도구
    기반 지표가 빠진다. 그 지표를 쓰는 채점 항목은 판정에서 제외된다
    (scoring.Rubric.applicable_criteria).

    impact_limb은 임팩트를 정의할 사지다 (루브릭의 kinematics.impact_limb).
    축구 슈팅은 다리, 농구 슛·야구 투구는 팔이다. 어느 쪽이든 다리·팔
    지표를 **둘 다** 산출하고, 루브릭이 measured_by로 쓸 것을 고른다.

    impact_event는 임팩트로 삼을 사건이다 (루브릭의 kinematics.impact_event).
    채찍질하는 동작은 extension_peak, 들어올려 놓는 동작은 distal_apex다.

    swing_side는 스윙 측을 직접 지정한다("left"/"right"). 기본값 "auto"는
    이동량으로 판별하는데, 팔 종목에서는 이 판별이 약하다(identify_limb 참고).
    던지는 팔·차는 발을 아는 사람이 지정하면 그 실패를 없앨 수 있다.

    **swing_side는 impact_limb에만 적용된다. 반대쪽 사지는 언제나 auto다.**
    일관성이 없어 보이지만 의도한 것이다 — "왼쪽"이 팔과 다리에서 같은 것을
    가리키지 않기 때문이다. 오른손 투수의 디딤발은 왼발이고, 오른발 슈팅에서
    크게 도는 팔은 왼팔이다. 사람이 아는 값은 **동작을 정의하는 사지 한쪽**
    ("던지는 팔은 왼쪽")뿐이며, 그 값을 반대쪽 사지에 그대로 넘기면 상당수
    동작에서 정확히 틀린 쪽을 지정하게 된다. 실제로 평가셋 39클립에서 자동
    판별된 팔 측과 다리 측은 44%에서만 일치했다 — 한 값이 둘을 대신할 수
    없다는 뜻이다.

    따라서 팔 루브릭에 swing_side="left"를 주면 다리 지표는 auto로 계산되고
    결과에도 그대로 실린다. 그 다리 지표는 **사람이 지정한 값이 아니다** —
    근거로 쓰기 전에 이 차이를 알고 있어야 한다. 반대쪽 사지까지 지정하려면
    인자를 하나 더 두어야 하고, 그럴 만한 요구는 아직 없다.
    """
    if impact_limb not in LIMB_CHAINS:
        raise ValueError(
            f"impact_limb은 {sorted(LIMB_CHAINS)} 중 하나여야 한다: {impact_limb!r}"
        )

    check_quality(kps, limb=impact_limb, side=swing_side)
    norm = normalize(kps)
    # 반대쪽 사지는 auto로 남긴다 — 팔의 "왼쪽"과 다리의 "왼쪽"은 같은 것을
    # 가리키지 않는다(오른손 투수의 디딤발은 왼발). docstring 참고.
    swing_knee, plant_knee = identify_legs(
        norm, swing_side if impact_limb == "leg" else "auto"
    )
    swing_chain, support_chain = identify_limb(norm, impact_limb, swing_side)
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

    # 골반 회전 — 골반 축 방향의 백스윙~임팩트 구간 변화폭.
    #
    # **벡터가 아니라 축으로 본다(mod 180).** 좌우 골반을 잇는 벡터로 재면
    # 몸이 돌아 좌/우 키포인트 라벨이 뒤바뀌는 순간 각도가 180도 점프한다 —
    # 야구 투구 실클립에서 프레임 6→7에 -4.5도 → -183.8도로 뛰었고, 실제 회전
    # 83도가 181.1도로 부풀어 **오측정이 최고 등급 장점이 됐다.** 골반의 방향은
    # 축이므로 좌우가 뒤집혀도 같은 자세다. mod 180으로 접으면 이 점프가 사라진다.
    #
    # 언랩은 그대로 필요하다. 접은 각도도 0~180 경계를 넘나들면 ptp가 부풀고,
    # 미검출 프레임은 골반 벡터가 (0,0)이라 각도가 0으로 튀므로 함께 제외한다.
    leg_usable = valid_frames(norm, "leg")
    hip_axis = _axis_deg(xy[:, L_HIP] - xy[:, R_HIP])
    shoulder_axis = _axis_deg(xy[:, L_SHOULDER] - xy[:, R_SHOULDER])
    tb_start, tb_end = phases.takeback
    span_idx = [f for f in range(tb_start, tb_end + 1) if leg_usable[f]]
    if len(span_idx) >= 2:
        unwrapped = np.unwrap(hip_axis[span_idx], period=180.0)
        hip_rotation_range = float(np.ptp(unwrapped))
    else:
        hip_rotation_range = 0.0

    # 골반-어깨 분리 — 골반이 얼마나 **먼저** 열렸는가.
    #
    # 회전량(위)과 다른 값이다. 회전량은 몸이 화면에서 돈 총량이라 카메라를 등지고
    # 도는 동작에서 커지기만 하고, "골반이 먼저 열리고 상체가 뒤따랐는가"는 담지
    # 못한다. 야구 루브릭의 hip_shoulder_separation 항목이 뜻하는 것은 이쪽이다.
    #
    # 두 축의 차이를 -90~90으로 접어 절대값을 쓰고, 준비 구간의 **최댓값**을
    # 취한다 — 분리는 앞발이 닿는 즈음 최대가 되고 릴리스에서 다시 좁혀진다.
    #
    # **몸통이 카메라를 향한 프레임은 뺀다.** 투영된 축이 짧아질수록 그 각도는
    # 불안정해진다 — 야구 투구 실클립에서 골반 축 길이가 0.44(정면)로 줄어든
    # 프레임이 분리각 81.2도를 냈다. 같은 클립의 축이 제대로 보이는 프레임에서는
    # 49.9도였다. 2D 투영으로 잴 수 없는 구간이므로 값을 만들지 않는다.
    trunk_ok = (
        (norm[:, [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP], 2] >= MIN_CONFIDENCE).all(axis=1)
        & (np.linalg.norm(xy[:, L_HIP] - xy[:, R_HIP], axis=1) >= MIN_AXIS_LENGTH)
        & (np.linalg.norm(xy[:, L_SHOULDER] - xy[:, R_SHOULDER], axis=1) >= MIN_AXIS_LENGTH)
    )
    sep = np.abs((shoulder_axis - hip_axis + 90.0) % 180.0 - 90.0)
    sep_idx = [f for f in range(tb_start, tb_end + 1) if trunk_ok[f]]

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

    # 몸통 키포인트가 부실하면 분리각을 내지 않는다 — 도구 미검출과 같은 규약으로
    # 그 지표를 쓰는 항목만 판정에서 빠지고, 남은 항목으로 가중치가 재정규화된다.
    if len(sep_idx) >= 2:
        features["hip_shoulder_separation_deg"] = round(float(sep[sep_idx].max()), 1)

    # 팔 지표 — 다리와 구조가 같다. 임팩트를 다리로 정의한 종목에서도 함께
    # 산출한다(상체 자세를 근거로 삼는 항목이 있을 수 있다). 신뢰도가 낮으면
    # NaN이 되므로 판정 근거로 쓰기 전에 걸러야 한다.
    # 다리 루브릭이면 팔 측은 auto다 — identify_legs 쪽과 같은 이유로,
    # 차는 발이 오른쪽이라고 해서 크게 도는 팔이 오른팔인 것은 아니다.
    arm_swing, arm_support = identify_limb(
        norm, "arm", swing_side if impact_limb == "arm" else "auto"
    )
    arm_swing_series = chain_series(norm, arm_swing)
    arm_support_series = chain_series(norm, arm_support)
    arm_usable = valid_frames(norm, "arm", arm_swing) & np.isfinite(arm_swing_series)
    arm_support_usable = valid_frames(norm, "arm", arm_support)
    if arm_usable[t]:
        features["swing_elbow_angle_at_impact"] = round(float(arm_swing_series[t]), 1)
        # 지지 팔은 스윙 팔과 따로 본다. 야구 투구처럼 글러브가 반대쪽 손을
        # 덮는 동작에서는 이 지표만 빠지고 나머지는 그대로 나온다.
        if arm_support_usable[t] and np.isfinite(arm_support_series[t]):
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

    return _drop_implausible(features)


def _drop_implausible(features: dict[str, float | int]) -> dict[str, float | int]:
    """물리적으로 불가능한 측정값을 뺀다 — 0등급이 아니라 미측정으로 다룬다.

    야구 투구 실클립에서 골반 회전 181.1도가 "40도 이상"이라는 열린 밴드에 걸려
    **최고 등급 장점으로 표시됐다.** 라벨 스왑에서 온 오측정이었다. 정의를 고쳐
    그 원인은 없앴지만, 다음 오측정도 같은 경로로 새어 나가지 않게 막는다.
    """
    return {
        k: v for k, v in features.items()
        if k not in PLAUSIBLE_RANGE
        or PLAUSIBLE_RANGE[k][0] <= float(v) <= PLAUSIBLE_RANGE[k][1]
    }


def verify_rubric_coverage(rubric, features: dict) -> None:
    """루브릭이 요구하는 지표를 파이프라인이 모두 산출했는지 검사한다.

    측정값에 없는 지표를 근거로 쓰게 두면 모델이 수치를 지어낸다.

    도구·사지 조건에 따라 빠질 수 있는 지표는 이번 영상에 없어도 통과시킨다 —
    다만 **이 모듈이 산출할 수 있다고 선언한 것**만 면제한다. 루브릭에 오타가
    나면 선언 목록에 없으므로 여전히 걸린다.
    """
    # PLAUSIBLE_RANGE의 지표는 범위 밖이면 빠질 수 있으므로 함께 면제한다.
    # **이름이 정확히 일치하는 것만** 면제되므로 루브릭 오타는 그대로 걸린다.
    optional = TOOL_DEPENDENT_METRICS | LIMB_DEPENDENT_METRICS | PLAUSIBLE_RANGE.keys()
    missing = rubric.required_metrics() - features.keys() - optional
    if missing:
        raise ValueError(
            f"루브릭이 요구하지만 파이프라인이 산출하지 않은 지표: {sorted(missing)}"
        )
