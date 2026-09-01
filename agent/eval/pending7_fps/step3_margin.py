"""3단계 — 왜 작은 섭동이 임팩트를 멀리 옮기는가.

가설: 전역 argmax의 **승자 마진이 얇다**. 클립 전체에서 각속도 피크 여러 개가
근소한 차이로 경쟁하므로, 격자든 스텐실이든 작은 섭동이 승자를 갈아치운다.
얇은 마진의 클립이 실제로 더 많이 옮겨 가는지 **예측 검정**한다.

덧붙여 스텐실 확대가 **날카로운 피크를 더 많이 깎는지**(차등 감쇠)를 잰다.

표 6  전역 argmax 승자 마진 분포
표 7  마진이 얇을수록 임팩트가 옮겨 가는가 (예측 검정)
표 8  스텐실 확대의 차등 감쇠 (step7이 짝수 프레임만으로 다시 잰다)
표 9  identify_limb 스윙 팔이 60fps와 달라지는 비율 — 부수 원인
"""
from __future__ import annotations

import numpy as np

from core import FACTORS, FPS_OF, external_pose_threshold, load_clips, side_of
from supersub_agent import features as F


def main() -> None:
    clips = load_clips()
    margin: list[float] = []
    moved: list[int] = []
    peak_atten: list[float] = []
    broad_atten: list[float] = []
    flip_by_k = {k: [0, 0] for k in FACTORS}

    with external_pose_threshold():
        for _name, kp in clips.items():
            try:
                norm60 = F.normalize(kp)
                sw60, _ = F.identify_limb(norm60, "arm", "auto")
                s60 = F.chain_series(norm60, sw60)
                u60 = F.valid_frames(norm60, "arm", sw60) & np.isfinite(s60)
                g60 = np.gradient(s60)
            except F.InsufficientQuality:
                continue

            for k in FACTORS:
                try:
                    nk = F.normalize(kp[::k])
                    sw, _ = F.identify_limb(nk, "arm", "auto")
                except F.InsufficientQuality:
                    continue
                flip_by_k[k][1] += 1
                flip_by_k[k][0] += int(side_of(sw) != side_of(sw60))

            if not u60.any():
                continue
            v = np.where(u60, g60, -np.inf)
            top = int(np.argmax(v))
            if not np.isfinite(v[top]) or v[top] <= 0:
                continue

            # 경쟁자 = top에서 5프레임 이상 떨어진 곳의 최댓값 (같은 사건의 어깨 제외)
            away = np.arange(len(v))
            rival_mask = np.abs(away - top) >= 5
            rival = v[rival_mask].max() if rival_mask.any() else -np.inf
            if not np.isfinite(rival) or rival <= 0:
                continue
            margin.append(v[top] / rival)

            try:
                n30 = F.normalize(kp[::2])
                sw30, _ = F.identify_limb(n30, "arm", "auto")
                s30 = F.chain_series(n30, sw30)
                u30 = F.valid_frames(n30, "arm", sw30) & np.isfinite(s30)
                a = F._peak_frame(np.gradient(s30), u30) * 2
            except (F.InsufficientQuality, ValueError):
                margin.pop()
                continue
            moved.append(abs(a - top))

            g30 = np.gradient(s30)
            half = top // 2
            if 0 < half < len(g30) - 1 and abs(g60[top]) > 1e-6:
                peak_atten.append(abs(g30[half]) / (2 * abs(g60[top])))
            slow = np.where(u60 & (np.abs(g60) < np.nanpercentile(np.abs(g60[u60]), 50)))[0]
            slow = [i for i in slow if 0 < i // 2 < len(g30) - 1 and abs(g60[i]) > 1e-6]
            if slow:
                broad_atten.append(float(np.median(
                    [abs(g30[i // 2]) / (2 * abs(g60[i])) for i in slow])))

    margin_a = np.array(margin)
    moved_a = np.array(moved)

    print(f"마진 분석 대상 {len(margin_a)}건\n")
    print("표 6 — 전역 argmax 승자 마진 (1위 / 5프레임 이상 떨어진 2위)")
    for q in (10, 25, 50, 75, 90):
        print(f"  p{q:<3} {np.percentile(margin_a, q):.2f}배")
    print(f"  마진 < 1.2배인 클립  {(margin_a < 1.2).mean() * 100:.0f}%")
    print(f"  마진 < 1.5배인 클립  {(margin_a < 1.5).mean() * 100:.0f}%")

    print("\n표 7 — 마진이 얇을수록 임팩트가 옮겨 가는가 (60→30)")
    print(f"{'마진 구간':>14} {'클립':>5} {'>2프레임 이동':>12} {'|이동| 중앙':>11}")
    for lo, hi in [(1.0, 1.1), (1.1, 1.3), (1.3, 1.8), (1.8, 3.0), (3.0, 1e9)]:
        sel = (margin_a >= lo) & (margin_a < hi)
        if sel.sum() == 0:
            continue
        label = f"{lo:.1f}~{hi:.1f}" if hi < 1e8 else f"{lo:.1f}+"
        print(f"{label:>14} {sel.sum():>5} {(moved_a[sel] > 2).mean() * 100:>11.0f}% "
              f"{np.median(moved_a[sel]):>10.0f}")
    r = np.corrcoef(np.log(margin_a), (moved_a > 2).astype(float))[0, 1]
    print(f"  상관(log 마진, 2프레임 초과 이동)  {r:+.2f}")

    print("\n표 8 — 스텐실 확대의 차등 감쇠 (선형이면 1.00, 작을수록 깎인 것)")
    print(f"  60fps 임팩트 프레임에서   {np.median(peak_atten):.2f}  (n={len(peak_atten)})")
    print(f"  완만한 구간(하위 50%)에서 {np.median(broad_atten):.2f}  (n={len(broad_atten)})")

    print("\n표 9 — identify_limb 스윙 팔이 60fps와 달라지는 비율")
    for k in FACTORS:
        n_flip, n = flip_by_k[k]
        print(f"  {FPS_OF[k]:>3}fps   {n_flip:>3}/{n}  ({n_flip / n * 100:.0f}%)")


if __name__ == "__main__":
    main()
