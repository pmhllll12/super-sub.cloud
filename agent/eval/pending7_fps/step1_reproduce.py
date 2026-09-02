"""1단계 — 08-26 증상을 먼저 재현한다 (60 vs 30fps 팔꿈치각).

여기서 재현되지 않으면 이후 분해는 의미가 없다.

표 1  fps별 통과율과 임팩트 팔꿈치각 분포 — 절벽이 30과 20 사이에 있는지
표 2  60 vs 30 공통 클립의 팔꿈치각 차이·임팩트 이동·스윙 팔 뒤집힘
"""
from __future__ import annotations

import json

import numpy as np

from core import FACTORS, FPS_OF, WORK, external_pose_threshold, load_clips, run_one


def main() -> None:
    clips = load_clips()
    with external_pose_threshold():
        res = {name: {k: run_one(kp, k) for k in FACTORS} for name, kp in clips.items()}

    print(f"클립 {len(clips)}건 (PitcherMotion 60fps, arm 임계 0.5)\n")

    print("표 1 — fps별 통과율과 임팩트 팔꿈치각 분포")
    print(f"{'fps':>4} {'통과':>6} {'팔꿈치각 중앙':>12} {'150~172 적중':>12}")
    for k in FACTORS:
        vals = [r[k]["elbow"] for r in res.values()
                if r[k]["ok"] and r[k].get("elbow_usable")]
        ok = sum(1 for r in res.values() if r[k]["ok"])
        hit = sum(1 for v in vals if 150 <= v <= 172)
        med = np.median(vals) if vals else float("nan")
        print(f"{FPS_OF[k]:>4} {ok:>6} {med:>11.1f}° "
              f"{(hit / len(vals) * 100 if vals else 0):>11.0f}%  (n={len(vals)})")

    pair = [n for n, r in res.items()
            if r[1]["ok"] and r[2]["ok"]
            and r[1].get("elbow_usable") and r[2].get("elbow_usable")]
    d = np.array([res[n][2]["elbow"] - res[n][1]["elbow"] for n in pair])
    shift = np.array([res[n][2]["impact_phys"] - res[n][1]["impact_phys"] for n in pair])
    flip = np.array([res[n][1]["swing"] != res[n][2]["swing"] for n in pair])

    print(f"\n표 2 — 60fps vs 30fps 공통 클립 {len(pair)}건")
    print(f"  |Δ팔꿈치각| 중앙       {np.median(np.abs(d)):.1f}°")
    print(f"  |Δ| > 10도             {(np.abs(d) > 10).mean() * 100:.0f}%  "
          f"({(np.abs(d) > 10).sum()}건)")
    print(f"  Δ = 정확히 0           {(d == 0).mean() * 100:.0f}%")
    print(f"  임팩트 물리프레임 동일 {(shift == 0).mean() * 100:.0f}%")
    print(f"  |임팩트 이동| 중앙     {np.median(np.abs(shift)):.0f} 물리프레임 "
          f"({np.median(np.abs(shift)) / 60:.2f}초)")
    print(f"  스윙 팔 좌우 뒤집힘    {flip.mean() * 100:.0f}%  ({flip.sum()}건)")

    WORK.mkdir(parents=True, exist_ok=True)
    np.savez(WORK / "step1.npz", pair=np.array(pair), d=d, shift=shift, flip=flip)
    with (WORK / "step1_res.json").open("w") as fh:
        json.dump({n: {str(k): v for k, v in r.items()} for n, r in res.items()}, fh)


if __name__ == "__main__":
    main()
