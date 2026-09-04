"""관절 데이터를 영상 없이 넣는 경로 (JHMDB → COCO-17).

🔴 **매핑이 틀리면 조용히 잘못된 각도가 나온다.** 예외도 경고도 없이 무릎각이
팔꿈치각 자리에 앉는다 — 그래서 여기서 잡는다.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

from supersub_agent import features as F

# scripts/ 는 패키지가 아니라 파일로 읽어 온다.
_SPEC = importlib.util.spec_from_file_location(
    "analyze_keypoints",
    Path(__file__).resolve().parent.parent / "scripts" / "analyze_keypoints.py",
)
AK = importlib.util.module_from_spec(_SPEC)
sys.modules["analyze_keypoints"] = AK
_SPEC.loader.exec_module(AK)


def test_mapping_covers_exactly_the_joints_features_reads():
    """features.py 가 읽는 12개가 **빠짐없이, 그리고 그것만** 채워져야 한다."""
    needed = {j for chains in F.LIMB_CHAINS.values()
              for chain in chains.values() for j in chain}
    assert len(needed) == 12

    filled = set(AK.JHMDB_TO_COCO.values())
    assert filled == needed, f"빠짐 {sorted(needed - filled)} · 군더더기 {sorted(filled - needed)}"

    # 두 관절이 같은 자리에 겹쳐 앉으면 하나가 조용히 덮인다.
    assert len(AK.JHMDB_TO_COCO) == len(filled)


def test_left_right_pairs_do_not_cross():
    """좌우가 뒤바뀌어 앉으면 스윙 측 판별이 통째로 뒤집힌다."""
    left_coco = {F.L_SHOULDER, F.L_ELBOW, F.L_WRIST, F.L_HIP, F.L_KNEE, F.L_ANKLE}
    # JHMDB 짝수 인덱스 4·6·8·10·12·14 가 왼쪽이다 (모듈 docstring 의 기하 확인).
    jhmdb_left = {4, 6, 8, 10, 12, 14}
    assert {AK.JHMDB_TO_COCO[j] for j in jhmdb_left} == left_coco


def test_conversion_puts_coordinates_where_they_belong():
    # 관절마다 알아볼 수 있는 값을 넣고 제자리에 앉는지 본다.
    pos = np.zeros((2, 15, 4))
    for j in range(15):
        pos[0, j, :] = 100 + j      # x
        pos[1, j, :] = 200 + j      # y
    kps = AK.jhmdb_to_coco(pos)

    assert kps.shape == (4, 17, 3)
    for src, dst in AK.JHMDB_TO_COCO.items():
        assert kps[0, dst, 0] == 100 + src
        assert kps[0, dst, 1] == 200 + src
        assert kps[0, dst, 2] == 1.0


def test_unused_coco_slots_stay_at_zero_confidence():
    """🔴 안 쓰는 자리를 1.0으로 채우면 게이트가 '있다'고 착각한다."""
    kps = AK.jhmdb_to_coco(np.ones((2, 15, 3)))
    for j in (F.NOSE, 1, 2, 3, 4):        # 코 · 눈 · 귀
        assert kps[:, j, 2].max() == 0.0


def test_bad_shape_is_rejected_instead_of_silently_reshaped():
    for bad in (np.zeros((2, 17, 5)), np.zeros((3, 15, 5)), np.zeros((15, 2))):
        try:
            AK.jhmdb_to_coco(bad)
        except ValueError:
            continue
        raise AssertionError(f"모양 {bad.shape}를 통과시켰다")


def test_converted_keypoints_run_through_extract_features():
    """끝에서 끝까지 — 관절만으로 지표가 나오는가."""
    from test_features import build_sequence

    seq = build_sequence()                     # (T, 17, 3) COCO
    # COCO → JHMDB 로 되돌려 넣고, 다시 변환해도 지표가 나와야 한다.
    pos = np.zeros((2, 15, seq.shape[0]))
    for src, dst in AK.JHMDB_TO_COCO.items():
        pos[0, src, :] = seq[:, dst, 0]
        pos[1, src, :] = seq[:, dst, 1]
    kps = AK.jhmdb_to_coco(pos)

    feats = F.extract_features(kps, None, "leg", "extension_peak", "auto")
    assert "impact_frame" in feats
    assert 0 <= feats["impact_frame"] < len(kps)
    # 공 궤적이 없으므로 도구 의존 지표는 안 나온다.
    assert "plant_foot_to_ball_offset" not in feats
