"""6단계 — 옮겨 간 임팩트는 어디로 가는가, 그리고 프레임 단위 규칙의 fps 의존.

(c) "10도 이상 차이가 시간축 어디에 분포하는가"에 답한다. 같은 물리 프레임의 각도는
    비트 단위로 같으므로(step2 표 5), 물어야 할 것은 **고른 프레임이 어디로 가는가**다.

표 19  임팩트가 클립 안에서 놓이는 상대 위치, 점프의 방향, 승자가 원래 경쟁자였는지
표 20  fps별 반려 사유 — 프레임 단위 경계 규칙의 fps 의존
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from core import FACTORS, FPS_OF, external_pose_threshold, load_clips, side_of
from supersub_agent import features as F


def main() -> None:
    clips = load_clips()
    pos60: list[float] = []
    pos30: list[float] = []
    jump: list[float] = []
    rival_was_peak: list[bool] = []
    reject: Counter = Counter()

    with external_pose_threshold():
        for _name, kp in clips.items():
            for k in FACTORS:
                sub = kp[::k]
                try:
                    n = F.normalize(sub)
                    sw, _ = F.identify_limb(n, "arm", "auto")
                    F.check_quality(sub, limb="arm", side="auto")
                    F.segment_phases(n, sw, "arm", "extension_peak")
                except F.InsufficientQuality as e:
                    key = ("경계 규칙(impact-first<2)" if "경계" in str(e)
                           else "게이트(유효비율)")
                    reject[(FPS_OF[k], key)] += 1
                except Exception:  # noqa: BLE001
                    reject[(FPS_OF[k], "기타")] += 1

            try:
                n60 = F.normalize(kp)
                sw60, _ = F.identify_limb(n60, "arm", "auto")
                s60 = F.chain_series(n60, sw60)
                u60 = F.valid_frames(n60, "arm", sw60) & np.isfinite(s60)
                g60 = np.gradient(s60)
                t60 = F._peak_frame(g60, u60)

                n30 = F.normalize(kp[::2])
                sw30, _ = F.identify_limb(n30, "arm", "auto")
                if side_of(sw30) != side_of(sw60):
                    continue
                s30 = F.chain_series(n30, sw30)
                u30 = F.valid_frames(n30, "arm", sw30) & np.isfinite(s30)
                t30 = F._peak_frame(np.gradient(s30), u30) * 2
            except (F.InsufficientQuality, ValueError):
                continue

            T = len(s60)
            pos60.append(t60 / T)
            pos30.append(t30 / T)
            jump.append((t30 - t60) / T)

            # 30fps가 고른 자리는 60fps에서도 이미 국소 피크였나
            lo, hi = max(1, t30 - 2), min(T - 1, t30 + 3)
            win = g60[lo:hi]
            rival_was_peak.append(bool(win.size and np.nanmax(win) > 0
                                       and np.nanmax(win) >= 0.5 * g60[t60]))

    p60 = np.array(pos60)
    p30 = np.array(pos30)
    jmp = np.array(jump)
    big = np.abs(jmp) > 0.05

    print(f"대상 {len(p60)}건\n")
    print("표 19 — 임팩트가 클립 안에서 놓이는 상대 위치 (0=시작, 1=끝)")
    for lbl, arr in (("60fps", p60), ("30fps", p30)):
        print(f"  {lbl}  중앙 {np.median(arr):.2f}   "
              f"앞 1/3에 놓임 {(arr < 1 / 3).mean() * 100:>3.0f}%   "
              f"뒤 1/3에 놓임 {(arr > 2 / 3).mean() * 100:>3.0f}%")
    print(f"\n  60→30에서 클립 길이의 5% 넘게 점프  {big.mean() * 100:.0f}%")
    print(f"  그중 앞으로(이르게) 이동            {(jmp[big] < 0).mean() * 100:.0f}%")
    print(f"  그중 뒤로(늦게) 이동                {(jmp[big] > 0).mean() * 100:.0f}%")
    print(f"  30fps 승자가 60fps에서도 국소 피크  "
          f"{np.mean(rival_was_peak) * 100:.0f}%  (새 인공물이 아니라 원래 경쟁자)")

    print("\n표 20 — fps별 반려 사유 (400클립)")
    print(f"{'fps':>5} {'게이트(유효비율)':>16} {'경계 규칙':>10} {'기타':>6}")
    for k in FACTORS:
        f = FPS_OF[k]
        print(f"{f:>5} {reject[(f, '게이트(유효비율)')]:>16} "
              f"{reject[(f, '경계 규칙(impact-first<2)')]:>10} "
              f"{reject[(f, '기타')]:>6}")


if __name__ == "__main__":
    main()
