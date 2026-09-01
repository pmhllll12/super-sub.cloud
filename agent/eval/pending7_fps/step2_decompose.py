"""2단계 — 임팩트 이동을 두 원인으로 분해한다. **이 조사의 핵심이다.**

  E1 후보 격자 축소 : 미분값은 60fps 그대로 두고 **argmax 후보만** 짝수 프레임으로
  E2 스텐실 확대   : 후보는 그대로 두고 **np.gradient 스텐실만** 2배로

  C = 60fps 실제        (60미분, 전 프레임)
  B = E1만              (60미분, 짝수 프레임)
  A = 30fps 실제        (30미분, 짝수 프레임) = E1 + E2

표 3  임팩트 프레임 이동의 원인 분해
표 4  각 원인이 만든 팔꿈치각 차이
표 5  부수 확인 — 같은 물리 프레임의 각도 동일성, 미분 단위 비율, travel 비율
"""
from __future__ import annotations

import numpy as np

from core import WORK, external_pose_threshold, load_clips, side_of
from supersub_agent import features as F


def main() -> None:
    clips = load_clips()
    rows: list[dict] = []
    angle_id_err: list[float] = []
    grad_ratio: list[float] = []
    travel_ratio: list[float] = []

    with external_pose_threshold():
        for name, kp in clips.items():
            try:
                norm60 = F.normalize(kp)
                sw60, _ = F.identify_limb(norm60, "arm", "auto")
                s60 = F.chain_series(norm60, sw60)
                u60 = F.valid_frames(norm60, "arm", sw60) & np.isfinite(s60)

                sub = kp[::2]
                norm30 = F.normalize(sub)
                sw30, _ = F.identify_limb(norm30, "arm", "auto")
                s30 = F.chain_series(norm30, sw30)
                u30 = F.valid_frames(norm30, "arm", sw30) & np.isfinite(s30)
            except F.InsufficientQuality:
                continue

            if side_of(sw60) != side_of(sw30):
                rows.append({"name": name, "flip": True})
                continue

            # (c) 같은 물리 프레임에서 각도가 같은가 — 정규화·데시메이션과 무관해야 한다
            m = np.isfinite(s60[::2]) & np.isfinite(s30)
            if m.any():
                angle_id_err.append(float(np.nanmax(np.abs(s60[::2][m] - s30[m]))))

            g60 = np.gradient(s60)
            g30 = np.gradient(s30)

            try:
                C = F._peak_frame(g60, u60)                       # 60fps 실제
                mask_even = np.zeros(len(s60), dtype=bool)
                mask_even[::2] = True
                B = F._peak_frame(g60, u60 & mask_even)           # E1만
                A = F._peak_frame(g30, u30) * 2                   # 30fps 실제
            except F.InsufficientQuality:
                continue

            common = np.arange(0, min(len(s60) // 2, len(s30)))
            ok = (np.isfinite(g60[::2][: len(common)])
                  & np.isfinite(g30[: len(common)]))
            if ok.sum() > 10:
                a = np.abs(g60[::2][: len(common)][ok])
                b = np.abs(g30[: len(common)][ok])
                sel = a > 1e-6
                if sel.any():
                    grad_ratio.append(float(np.median(b[sel] / a[sel])))

            xy60, xy30 = norm60[:, :, :2], norm30[:, :, :2]
            t60 = float(np.linalg.norm(np.diff(xy60[:, sw60[2]], axis=0), axis=1).sum())
            t30 = float(np.linalg.norm(np.diff(xy30[:, sw30[2]], axis=0), axis=1).sum())
            if t60 > 1e-9:
                travel_ratio.append(t30 / t60)

            rows.append({
                "name": name, "flip": False, "A": A, "B": B, "C": C,
                "ang_A": float(s60[A]) if A < len(s60) and np.isfinite(s60[A]) else np.nan,
                "ang_B": float(s60[B]),
                "ang_C": float(s60[C]),
            })

    good = [r for r in rows if not r["flip"] and np.isfinite(r.get("ang_A", np.nan))]
    A = np.array([r["A"] for r in good])
    B = np.array([r["B"] for r in good])
    C = np.array([r["C"] for r in good])

    print(f"분해 대상 {len(good)}건 (스윙 팔이 60/30에서 같은 클립)\n")
    print("표 3 — 임팩트 프레임 이동의 원인 분해 (물리 프레임 = 60fps 인덱스)")
    print(f"  C→A 전체 이동     동일 {np.mean(A == C) * 100:>5.0f}%   "
          f"|이동| 중앙 {np.median(np.abs(A - C)):>4.0f}   평균 {np.mean(np.abs(A - C)):>6.1f}")
    print(f"  C→B 후보격자만    동일 {np.mean(B == C) * 100:>5.0f}%   "
          f"|이동| 중앙 {np.median(np.abs(B - C)):>4.0f}   평균 {np.mean(np.abs(B - C)):>6.1f}")
    print(f"  B→A 스텐실만      동일 {np.mean(A == B) * 100:>5.0f}%   "
          f"|이동| 중앙 {np.median(np.abs(A - B)):>4.0f}   평균 {np.mean(np.abs(A - B)):>6.1f}")

    near = np.abs(B - C) <= 1
    print(f"\n  C→B 이동이 ≤1프레임인 비율   {near.mean() * 100:.0f}%   "
          f"(격자 반올림으로 설명되는 몫)")
    far = np.abs(A - B) > 1
    print(f"  B→A 이동이 >1프레임인 비율   {far.mean() * 100:.0f}%   "
          f"(스텐실이 다른 사건을 고른 몫)")

    dA = np.array([r["ang_A"] - r["ang_C"] for r in good])
    dB = np.array([r["ang_B"] - r["ang_C"] for r in good])
    dAB = np.array([r["ang_A"] - r["ang_B"] for r in good])
    print("\n표 4 — 각 원인이 만든 팔꿈치각 차이")
    print(f"  전체(C→A)      |Δ| 중앙 {np.median(np.abs(dA)):>5.1f}°   "
          f">10도 {(np.abs(dA) > 10).mean() * 100:>3.0f}%")
    print(f"  후보격자만(C→B) |Δ| 중앙 {np.median(np.abs(dB)):>5.1f}°   "
          f">10도 {(np.abs(dB) > 10).mean() * 100:>3.0f}%")
    print(f"  스텐실만(B→A)   |Δ| 중앙 {np.median(np.abs(dAB)):>5.1f}°   "
          f">10도 {(np.abs(dAB) > 10).mean() * 100:>3.0f}%")

    print("\n표 5 — 부수 확인")
    print(f"  같은 물리 프레임 팔꿈치각 최대 오차   {max(angle_id_err):.2e}도 "
          f"(n={len(angle_id_err)})")
    print(f"  |np.gradient| 30fps / 60fps 중앙비    {np.median(grad_ratio):.2f}배 "
          f"(단위가 도/프레임이라 예상 2.00)")
    print(f"  identify_limb travel 30fps / 60fps    {np.median(travel_ratio):.2f}배")
    print(f"  스윙 팔 좌우 뒤집힌 클립              "
          f"{sum(1 for r in rows if r['flip'])}/{len(rows)}")

    WORK.mkdir(parents=True, exist_ok=True)
    np.savez(WORK / "step2.npz", A=A, B=B, C=C, dA=dA, dB=dB, dAB=dAB)


if __name__ == "__main__":
    main()
