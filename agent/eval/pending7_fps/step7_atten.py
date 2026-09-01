"""7단계 — 차등 감쇠를 짝수 프레임(격자에 실제로 남는 자리)으로만 다시 잰다.

step3 표 8은 60fps 임팩트가 홀수 프레임일 때 30fps 격자에 그 자리가 아예 없어
감쇠를 과대평가한다. 여기서는 짝수 임팩트만 골라 다시 잰다 — **이 값이 보고용이다.**
"""
from __future__ import annotations

import numpy as np

from core import external_pose_threshold, load_clips
from supersub_agent import features as F


def main() -> None:
    peak: list[float] = []
    broad: list[float] = []

    with external_pose_threshold():
        for _name, kp in load_clips().items():
            try:
                n = F.normalize(kp)
                sw, _ = F.identify_limb(n, "arm", "auto")
                s = F.chain_series(n, sw)
                u = F.valid_frames(n, "arm", sw) & np.isfinite(s)
                g60 = np.gradient(s)
                g30 = np.gradient(s[::2])
                t = F._peak_frame(g60, u)
            except (F.InsufficientQuality, ValueError):
                continue
            if t % 2 or not (0 < t // 2 < len(g30) - 1) or abs(g60[t]) < 1e-6:
                continue
            peak.append(abs(g30[t // 2]) / (2 * abs(g60[t])))
            med = np.nanpercentile(np.abs(g60[u]), 50)
            idx = [i for i in np.where(u & (np.abs(g60) < med))[0]
                   if i % 2 == 0 and 0 < i // 2 < len(g30) - 1 and abs(g60[i]) > 1e-6]
            if idx:
                broad.append(float(np.median(
                    [abs(g30[i // 2]) / (2 * abs(g60[i])) for i in idx])))

    print(f"짝수 임팩트 프레임만 (n={len(peak)})")
    print(f"  임팩트 프레임 감쇠   {np.median(peak):.2f}")
    print(f"  완만한 구간 감쇠     {np.median(broad):.2f}  (n={len(broad)})")
    print(f"  차등 배율            {np.median(broad) / np.median(peak):.2f}배")


if __name__ == "__main__":
    main()
