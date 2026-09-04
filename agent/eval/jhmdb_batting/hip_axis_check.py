#!/usr/bin/env python3
"""골반 회전 지표가 타격에서 무엇을 재는지 확인한다 (실클립 기록 4절의 가설).

    uv run python eval/jhmdb_batting/hip_axis_check.py \
        --root /mnt/d/sports_dataset/_jhmdb/joint_positions

## 무엇을 묻나

`hip_rotation_range_deg`는 좌우 골반을 잇는 선의 **화면 평면 각도** 변화폭이다
(`features._axis_deg`). 그런데 타격의 골반 회전은 **수직축 둘레의 회전**이라,
측면에서 보면 그 선은 화면에서 **돌지 않고 짧아진다.**

그렇다면 준비~임팩트 구간에서 **각도는 거의 안 변하는데 길이는 크게 줄어드는**
클립이 많아야 한다. 그 두 값을 같은 구간에서 나란히 재서 비교한다.

🔴 **이것은 정확도 측정이 아니다.** 정답이 없다. 재는 것은 "두 양이 같은 것을
가리키는가"이고, 답이 '아니다'라면 그 항목은 **임계값 문제가 아니라 타당성
문제**라는 뜻이다.

길이는 어깨너비로 정규화된 값이다(`features.normalize`) — 촬영 거리가 아니라
자세 때문에 짧아진 것만 남는다.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from supersub_agent import features as F  # noqa: E402
from analyze_keypoints import load_jhmdb  # noqa: E402


def hip_axis_span(kps: np.ndarray) -> tuple[float, float] | None:
    """준비~임팩트 구간의 (골반 축 각도 변화폭, 축 단축률).

    각도는 `extract_features`가 쓰는 것과 **같은 산술**이다 — 축 기준(mod 180)
    으로 접고 언랩한 뒤 ptp. 단축률은 같은 구간에서 `1 - min/max`다.
    """
    norm = F.normalize(kps)
    swing, _ = F.identify_limb(norm, "arm", "auto")
    phases = F.segment_phases(norm, swing, "arm", "extension_peak")

    xy = norm[:, :, :2]
    hip_axis = F._axis_deg(xy[:, F.L_HIP] - xy[:, F.R_HIP])
    hip_len = np.linalg.norm(xy[:, F.L_HIP] - xy[:, F.R_HIP], axis=1)

    leg_usable = F.valid_frames(norm, "leg")
    lo, hi = phases.takeback
    idx = [f for f in range(lo, hi + 1) if leg_usable[f]]
    if len(idx) < 2:
        return None

    angle_range = float(np.ptp(np.unwrap(hip_axis[idx], period=180.0)))
    lengths = hip_len[idx]
    top = float(lengths.max())
    if top <= 1e-6:
        return None
    return angle_range, float(1.0 - lengths.min() / top)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--action", default="swing_baseball")
    args = ap.parse_args()

    angles, shortenings = [], []
    for name, kps in load_jhmdb(args.root, args.action):
        try:
            out = hip_axis_span(kps)
        except (F.InsufficientQuality, ValueError):
            continue
        if out is None:
            continue
        angles.append(out[0])
        shortenings.append(out[1])

    n = len(angles)
    if not n:
        raise SystemExit("측정된 클립이 없다")

    def q(vals, p):
        return round(sorted(vals)[min(int(len(vals) * p), len(vals) - 1)], 3)

    print(f"{args.action}: {n}클립 (준비~임팩트 구간)")
    print(f"  골반 축 각도 변화폭(도)  중앙 {q(angles,.5):7.1f}"
          f"   25% {q(angles,.25):7.1f}   75% {q(angles,.75):7.1f}   max {max(angles):7.1f}")
    print(f"  골반 축 단축률           중앙 {q(shortenings,.5):7.3f}"
          f"   25% {q(shortenings,.25):7.3f}   75% {q(shortenings,.75):7.3f}   max {max(shortenings):7.3f}")

    # 이 루브릭의 2등급 하한은 30도다.
    below = sum(a < 30 for a in angles)
    big_shortening = sum(s >= 0.3 for s in shortenings)
    both = sum(a < 30 and s >= 0.3 for a, s in zip(angles, shortenings))
    print(f"\n  각도 30도 미만            {below}/{n}")
    print(f"  단축률 0.3 이상           {big_shortening}/{n}")
    print(f"  🔴 둘 다 (안 돌았는데 짧아짐) {both}/{n}")
    if angles and shortenings and n >= 3:
        r = float(np.corrcoef(angles, shortenings)[0, 1])
        print(f"\n  두 값의 상관             {r:+.3f}  "
              "(0 근처면 서로 다른 것을 재고 있다는 뜻이다)")


if __name__ == "__main__":
    main()
