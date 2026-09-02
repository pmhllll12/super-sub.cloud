"""4단계 — 각도 차이가 어디서 등급 차이가 되는가.

야구 투구 루브릭(active)으로 지표 → 등급 → 총점까지 태워 60fps 대비 변화를 센다.
판정 모델은 부르지 않는다 — 등급은 scoring.Criterion.grade_for가 정한다.

표 10  지표 산출 성공률
표 11  지표별 60fps 대비 30fps 변화
표 12  항목별 등급이 바뀐 비율
표 13  총점·최종 등급 변화
표 14  경계 근처 밀집도
표 15  fps별 총점
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from core import (
    FACTORS,
    FPS_OF,
    RUBRIC_BASEBALL,
    external_pose_threshold,
    load_clips,
    run_features,
)
from supersub_agent import scoring

METRICS = [
    "swing_elbow_angle_at_impact", "plant_knee_angle_at_impact",
    "trunk_forward_lean_deg_at_impact", "hip_shoulder_separation_deg",
    "swing_shoulder_flexion_after_impact_deg", "hip_rotation_range_deg",
    "follow_through_duration_frames", "impact_frame",
]


def main() -> None:
    rubric = scoring.load_rubric(RUBRIC_BASEBALL)
    clips = load_clips()

    with external_pose_threshold():
        feats = {name: {k: run_features(kp, k) for k in FACTORS}
                 for name, kp in clips.items()}

    def score_of(f: dict) -> dict:
        judged = {c.id: {"grade": c.grade_for(f), "evidence": "", "metric_ref": ""}
                  for c in rubric.applicable_criteria(f)}
        return scoring.aggregate(judged, rubric)

    print("표 10 — 지표 산출 성공률")
    for k in FACTORS:
        n = sum(1 for v in feats.values() if v[k] is not None)
        print(f"  {FPS_OF[k]:>3}fps  {n}/{len(feats)}")

    base = [n for n, v in feats.items() if v[1] is not None and v[2] is not None]
    print(f"\n60fps·30fps 둘 다 산출된 클립 {len(base)}건")

    print("\n표 11 — 지표별 60fps 대비 30fps 변화")
    print(f"{'지표':>42} {'n':>4} {'동일':>6} {'|Δ| 중앙':>9} {'30/60 중앙비':>12}")
    for m in METRICS:
        pairs = [(feats[n][1][m], feats[n][2][m]) for n in base
                 if m in feats[n][1] and m in feats[n][2]]
        if not pairs:
            continue
        a = np.array([p[0] for p in pairs], dtype=float)
        b = np.array([p[1] for p in pairs], dtype=float)
        ratio = np.median(b[a != 0] / a[a != 0]) if (a != 0).any() else float("nan")
        print(f"{m:>42} {len(pairs):>4} {(a == b).mean() * 100:>5.0f}% "
              f"{np.median(np.abs(b - a)):>8.1f} {ratio:>11.2f}")

    print("\n표 12 — 항목별 등급이 바뀐 비율 (60fps → 30fps)")
    print(f"{'항목':>28} {'n':>4} {'등급 변화':>9} {'경계 마진 중앙':>14}")
    for c in rubric.criteria:
        rows = [(feats[n][1], feats[n][2]) for n in base
                if c.is_applicable(feats[n][1]) and c.is_applicable(feats[n][2])]
        if not rows:
            continue
        chg = sum(1 for f1, f2 in rows if c.grade_for(f1) != c.grade_for(f2))
        marg = np.median([c.band_margin(f1) for f1, _ in rows])
        print(f"{c.name:>28} {len(rows):>4} {chg / len(rows) * 100:>8.0f}% {marg:>13.2f}")

    print("\n표 13 — 총점·등급 변화 (60fps → 30fps)")
    sc = [(score_of(feats[n][1]), score_of(feats[n][2])) for n in base]
    d = np.array([b["score"] - a["score"] for a, b in sc])
    gchg = sum(1 for a, b in sc if a["grade"] != b["grade"])
    print(f"  총점 동일          {(d == 0).mean() * 100:.0f}%")
    print(f"  |Δ총점| 중앙       {np.median(np.abs(d)):.0f}점   최대 {np.abs(d).max():.0f}점")
    print(f"  최종 등급(A~D) 변화 {gchg}/{len(sc)}  ({gchg / len(sc) * 100:.0f}%)")
    print("  등급 이동 분포     "
          f"{Counter((a['grade'], b['grade']) for a, b in sc if a['grade'] != b['grade']).most_common(6)}")

    print("\n표 14 — 경계 근처에 값이 몰려 있는가 (60fps 기준, margin<0.1 = 구간폭의 10% 안)")
    for c in rubric.criteria:
        ms = [c.band_margin(feats[n][1]) for n in base if c.is_applicable(feats[n][1])]
        if not ms:
            continue
        ms = np.array(ms)
        print(f"{c.name:>28}  margin<0.1 {(ms < 0.1).mean() * 100:>3.0f}%   "
              f"<0.2 {(ms < 0.2).mean() * 100:>3.0f}%")

    print("\n표 15 — fps별 총점 (공통 클립만)")
    common = [n for n, v in feats.items() if all(v[k] is not None for k in FACTORS)]
    print(f"  공통 클립 {len(common)}건")
    for k in FACTORS:
        s = [score_of(feats[n][k])["score"] for n in common]
        print(f"  {FPS_OF[k]:>3}fps  총점 중앙 {np.median(s):>5.0f}   평균 {np.mean(s):>5.1f}")


if __name__ == "__main__":
    main()
