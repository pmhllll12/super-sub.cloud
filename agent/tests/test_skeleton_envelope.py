"""`skeleton` 봉투 — 비교 화면이 겹쳐 그리는 관절과 세 순간 (미결 `paik` 30번).

🔴 **여기 있는 검사 몇 개는 지우면 안 된다.** 막고 있는 것은 이것이다:

화면은 이 값으로 **자세 세 장을 겹쳐 그린다.** 프레임 번호가 하나 밀리거나
못 잡은 프레임이 배열에서 빠지면 **예외도 경고도 없이 다른 자세가 그려진다** —
스켈레톤은 늘 그럴듯해 보이므로 눈으로도 안 잡힌다. 그리고 임팩트를 여기서
다시 찾으면 리포트의 임팩트와 화면의 임팩트가 갈리는데, 둘 다 「임팩트」라고
적혀 있어서 어느 쪽이 틀렸는지 사후에 가릴 수 없다.
"""
from __future__ import annotations

import numpy as np
import pytest

import supersub_agent.features as F
from supersub_agent.features import (
    KEYPOINT_NAMES,
    extract_features,
    skeleton_envelope,
)
from test_features import build_sequence

FRAME_SIZE = (1920, 1080)
FPS = 15.0


def pixelize(kps: np.ndarray) -> np.ndarray:
    """합성 시퀀스를 **픽셀 좌표계**로 옮긴다.

    `build_sequence` 는 골반 중심이 원점인 정규화 공간을 내는데, 이 봉투가
    받는 것은 ViTPose 의 **이미지 픽셀** 출력이다. 원점 그대로 두고 검사하면
    "프레임 크기로 나눈다"는 성질이 0 근처에서만 확인된다.
    """
    out = kps.copy()
    out[:, :, 0] = out[:, :, 0] * 120.0 + 960.0
    out[:, :, 1] = out[:, :, 1] * 120.0 + 540.0
    return out


def envelope(kps: np.ndarray, side: str = "auto") -> tuple[dict, dict]:
    """(`skeleton` 봉투, `features`) — production 함수를 그대로 지나온 것."""
    features = extract_features(kps, {}, "leg", "extension_peak", side)
    block = skeleton_envelope(kps, FPS, features, "leg", side, FRAME_SIZE)
    return block, features


@pytest.fixture(scope="module")
def clip() -> np.ndarray:
    return pixelize(build_sequence())


def test_the_impact_is_the_one_scoring_already_chose(clip):
    """🔴 **지우지 말 것** — 임팩트를 여기서 다시 찾으면 안 된다.

    `segment_phases` 가 고른 값을 그대로 실어야 리포트의 임팩트와 화면이
    겹쳐 그리는 임팩트가 같다. 규칙을 두 벌로 두면 둘이 갈리는데 **양쪽 다
    「임팩트」라고 적혀 있어서** 어느 쪽이 틀렸는지 알 수 없다.
    """
    block, features = envelope(clip)
    assert block["moments"]["impact"] == int(features["impact_frame"])


def test_joints_keep_one_slot_per_frame_including_the_ones_we_did_not_catch():
    """🔴 **지우지 말 것** — 못 잡은 프레임이 배열에서 빠지면 안 된다.

    빠지면 배열 인덱스와 프레임 번호가 어긋나고, 세 순간이 **엉뚱한 자세**를
    가리킨다. 29번이 확인 조건으로 요구한 성질이기도 하다.
    """
    kps = pixelize(build_sequence())
    kps[5, :, 2] = 0.0          # 사람이 안 잡힌 프레임 — pose.py 가 이렇게 채운다
    kps[6, :, 2] = 0.0
    block, _ = envelope(kps)

    assert len(block["joints"]) == block["frames"] == len(kps)
    assert block["joints"][5] is None and block["joints"][6] is None
    assert block["joints"][0] is not None
    # 자리를 지킨다 = 뒤 프레임이 앞으로 당겨지지 않았다.
    assert block["joints"][7] is not None


def test_each_joint_row_is_seventeen_points_of_x_y_confidence(clip):
    block, _ = envelope(clip)
    row = next(r for r in block["joints"] if r is not None)
    assert len(row) == 17
    assert all(len(p) == 3 for p in row)
    assert block["keypoint_names"] == list(KEYPOINT_NAMES)


def test_coordinates_are_divided_by_the_frame_size(clip):
    """픽셀이 아니라 프레임 크기로 나눈 값이어야 화면이 바로 겹칠 수 있다."""
    block, _ = envelope(clip)
    t = block["moments"]["impact"]
    row = block["joints"][t]
    assert row is not None
    for j, (x, y, _c) in enumerate(row):
        assert x == pytest.approx(clip[t, j, 0] / FRAME_SIZE[0], abs=1e-4)
        assert y == pytest.approx(clip[t, j, 1] / FRAME_SIZE[1], abs=1e-4)


def test_coordinates_outside_the_frame_are_not_clipped():
    """🔴 0~1로 자르면 화면 밖으로 나간 발이 **가장자리에 붙어** 그려진다."""
    kps = pixelize(build_sequence())
    kps[:, F.L_ANKLE, 0] = -240.0        # 왼쪽 밖으로 나간 발
    block, _ = envelope(kps)
    row = block["joints"][block["moments"]["impact"]]
    assert row is not None
    assert row[F.L_ANKLE][0] < 0.0


def test_the_before_moment_sits_three_tenths_of_a_second_earlier(clip):
    block, features = envelope(clip)
    impact = int(features["impact_frame"])
    assert block["moments"]["before"] == impact - round(0.3 * FPS)


def test_the_before_moment_falls_back_when_the_swing_knee_is_not_there():
    """「직전」 프레임에 차는 다리 무릎각이 없으면 가장 가까운 잡힌 프레임.

    그 카드가 보여주는 것이 무릎 굽힘이라, 다른 관절이 잡혀 있어도 소용이 없다.
    """
    kps = pixelize(build_sequence())
    features = extract_features(kps, {}, "leg", "extension_peak", "auto")
    impact = int(features["impact_frame"])
    wanted = impact - round(0.3 * FPS)

    # 무릎만 떨어뜨린다 — 프레임 자체는 잡혀 있다(다른 관절 신뢰도 그대로).
    swing_leg = skeleton_envelope(
        kps, FPS, features, "leg", "auto", FRAME_SIZE
    )["swing_leg"]
    knee = F.L_KNEE if swing_leg == "left" else F.R_KNEE
    kps[wanted, knee, 2] = 0.0

    block, _ = envelope(kps)
    assert block["moments"]["before"] != wanted
    assert abs(block["moments"]["before"] - wanted) == 1
    # 프레임 자체는 살아 있다 — 「안 잡힌 프레임」과 다른 사유다.
    assert block["joints"][wanted] is not None


def test_a_tie_in_the_fallback_takes_the_earlier_frame():
    """양옆이 똑같이 가까우면 **이른 쪽**. 안 정해 두면 경로마다 달라진다."""
    usable = np.array([True, True, False, True, True])
    assert F._nearest_valid(usable, 2) == 1


def test_the_after_moment_falls_back_to_the_last_usable_frame_when_it_overflows():
    """+1초가 클립을 넘치면 마지막 유효 프레임."""
    kps = pixelize(build_sequence(n=25, impact=16))
    block, features = envelope(kps)
    impact = int(features["impact_frame"])
    assert impact + round(FPS) >= len(kps), "이 클립은 +1초가 넘쳐야 한다"
    assert block["moments"]["after"] < len(kps)
    assert block["joints"][block["moments"]["after"]] is not None


def test_the_swing_leg_is_the_one_the_metrics_were_measured_on(clip):
    """🔴 **지우지 말 것** — 「차는 다리」가 채점과 갈리면 안 된다.

    화면은 이 이름으로 「차는 다리 무릎 굽히기」 카드를 그리는데, 값은 리포트의
    `swing_knee_angle_at_impact` 에서 온다. 둘이 갈리면 **반대쪽 다리의 각도를
    차는 다리라고 설명**하게 되고, 스켈레톤은 어느 쪽이든 그럴듯해 보인다.

    그래서 이름이 아니라 **그 이름이 가리키는 무릎의 각도**를 대 본다 —
    `identify_legs` 를 다시 불러 비교하면 같은 함수끼리의 대조라 안 갈린다.
    """
    block, features = envelope(clip)
    impact = int(features["impact_frame"])
    knee = F.L_KNEE if block["swing_leg"] == "left" else F.R_KNEE
    measured = F._knee_series(F.normalize(clip), knee)[impact]
    assert measured == pytest.approx(features["swing_knee_angle_at_impact"], abs=0.05)

    # 반대쪽이었다면 이 검사가 실제로 갈렸을 것 — 공허하게 통과하지 않는다.
    other = F.R_KNEE if knee == F.L_KNEE else F.L_KNEE
    assert F._knee_series(F.normalize(clip), other)[impact] != pytest.approx(
        features["swing_knee_angle_at_impact"], abs=0.05
    )


def test_the_block_does_not_change_the_judging_input(clip):
    """🔴 **지우지 말 것** — `features` 의 형제 블록이라는 성질이 값이다.

    여기서 `features` 에 키가 하나라도 늘면 판정 입력이 달라져 **B-6 재실행**
    을 부르고, 그때까지의 평가가 전부 무효가 된다 (`agent/CLAUDE.md` 「값비싼
    실수 (1)」).
    """
    features = extract_features(clip, {}, "leg", "extension_peak", "auto")
    before = dict(features)
    skeleton_envelope(clip, FPS, features, "leg", "auto", FRAME_SIZE)
    assert features == before


def test_seconds_come_from_the_effective_fps(clip):
    """읽는 쪽이 `target_fps` 로 나누면 20% 어긋난다 — 그래서 초를 함께 낸다."""
    block, _ = envelope(clip)
    for key, frame in block["moments"].items():
        assert block["moments_seconds"][key] == pytest.approx(frame / FPS, abs=5e-4)


def test_a_path_without_a_frame_size_says_it_does_not_know(clip):
    """픽셀 크기를 모르면 정규화가 성립하지 않는다 — 픽셀을 대신 내지 않는다."""
    features = extract_features(clip, {}, "leg", "extension_peak", "auto")
    block = skeleton_envelope(clip, FPS, features, "leg", "auto", None)
    assert block["known"] is False
    assert "joints" not in block


def test_an_unusable_fps_is_not_papered_over(clip):
    features = extract_features(clip, {}, "leg", "extension_peak", "auto")
    block = skeleton_envelope(clip, 0.0, features, "leg", "auto", FRAME_SIZE)
    assert block["known"] is False


def test_keypoint_names_line_up_with_the_index_constants():
    """이름표와 인덱스가 갈리면 **왼쪽 무릎을 오른쪽으로** 그려도 안 터진다."""
    assert len(KEYPOINT_NAMES) == 17
    for name, idx in (
        ("nose", F.NOSE),
        ("left_shoulder", F.L_SHOULDER), ("right_shoulder", F.R_SHOULDER),
        ("left_elbow", F.L_ELBOW), ("right_elbow", F.R_ELBOW),
        ("left_wrist", F.L_WRIST), ("right_wrist", F.R_WRIST),
        ("left_hip", F.L_HIP), ("right_hip", F.R_HIP),
        ("left_knee", F.L_KNEE), ("right_knee", F.R_KNEE),
        ("left_ankle", F.L_ANKLE), ("right_ankle", F.R_ANKLE),
    ):
        assert KEYPOINT_NAMES[idx] == name
