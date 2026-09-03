"""미결 6번 — 기록된 travel 수치를 현재 동작점에서 재계산한다. **GPU 불필요.**

`extract.py`가 남긴 `cache/*.npz`만 읽는다. 덤프는 target 30(실효 25fps /
23.98fps)으로 뽑았고, `read_frames`가 정수 간격으로 솎으므로 `[::2]`가
**옛 동작점(target 15 → 실효 12.5fps / 11.99fps)의 정확한 프레임 부분집합**이다.
ViTPose는 프레임마다 독립으로 돌므로 솎아 낸 결과는 그 fps로 다시 돌린 것과
같다 — 그래서 옛 수치와 새 수치를 같은 덤프에서 나란히 낼 수 있다.

    cd agent && .venv/bin/python eval/pending6_side/recompute.py

production code는 **import만** 한다. 판별 로직(identify_limb)을 다시 구현하지
않고 그대로 호출한다 — 재구현하면 본체가 바뀌어도 여기서는 옛 값이 나온다.
travel만 본체에 없는 값이라 여기서 계산하되 identify_limb과 같은 식을 쓴다.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent
CACHE = HERE / "cache"

if importlib.util.find_spec("supersub_agent") is None:  # pragma: no cover
    sys.path.insert(0, str(AGENT / "src"))

from supersub_agent import features as F  # noqa: E402

# 옛 동작점 재현용 솎음 간격. 두 클립 모두 target 15에서 step=2였다
# (25/15 → round 2, 23.98/15 → round 2).
OLD_STEP = 2


def travel(norm: np.ndarray, chain: tuple[int, int, int]) -> float:
    """identify_limb 안의 travel과 같은 식 — 말단 관절 경로 길이."""
    distal = norm[:, chain[2], :2]
    return float(np.linalg.norm(np.diff(distal, axis=0), axis=1).sum())


def report(cid: str, sampled_fps: float, kps: np.ndarray, tag: str) -> dict:
    norm = F.normalize(kps)
    out = {"tag": tag, "fps": sampled_fps, "T": len(kps)}
    print(f"\n  [{tag}] {len(kps)}프레임 실효 {sampled_fps:.2f}fps")
    for limb in ("arm", "leg"):
        chains = F.LIMB_CHAINS[limb]
        tl, tr = travel(norm, chains["left"]), travel(norm, chains["right"])
        swing, _ = F.identify_limb(norm, limb)
        picked = "left" if swing == chains["left"] else "right"
        margin = abs(tl - tr) / max(tl, tr) * 100.0
        out[limb] = {"left": tl, "right": tr, "picked": picked, "margin_pct": margin}
        print(
            f"    {limb:<4} left {tl:7.2f}  right {tr:7.2f}"
            f"  → 스윙 {picked:<5} (마진 {margin:.1f}%)"
        )
        # 체인 전체 신뢰도 — 경로가 노이즈로 부풀었는지 보는 근거.
        # docstring이 "글러브 팔 신뢰도 0.3~0.6"이라고 쓴 값이 이것이다.
        for side in ("left", "right"):
            c = kps[:, list(chains[side]), 2]
            print(
                f"         {side:<5} 체인 신뢰도 중앙 {np.median(c):.2f} "
                f"(말단 {np.median(c[:, 2]):.2f}, 세 관절 모두 "
                f"≥{F.LIMB_MIN_CONFIDENCE[limb]}인 프레임 "
                f"{(c >= F.LIMB_MIN_CONFIDENCE[limb]).all(axis=1).mean():.0%})"
            )
        # 경로가 몇 프레임에 몰려 있는가 — "릴리스가 두 프레임 안에 끝난다"는
        # docstring의 인과가 이 분포를 두고 한 말이다.
        for side in ("left", "right"):
            step = np.linalg.norm(np.diff(norm[:, chains[side][2], :2], axis=0), axis=1)
            top = np.sort(step)[::-1]
            total = top.sum()
            print(
                f"         {side:<5} 상위 2프레임이 경로의 "
                f"{top[:2].sum() / total:.0%}, 상위 4프레임 "
                f"{top[:4].sum() / total:.0%}"
            )
    return out


def main() -> None:
    for npz in sorted(CACHE.glob("*.npz")):
        d = np.load(npz)
        kps, fps = d["keypoints"], float(d["sampled_fps"])
        print(f"\n=== {npz.stem} (원본 {float(d['source_fps']):.2f}fps) ===")
        new = report(npz.stem, fps, kps, "현재 target 30")
        old = report(npz.stem, fps / OLD_STEP, kps[::OLD_STEP], "옛 target 15")

        print("\n    fps를 2배로 올렸을 때 travel 배율 (옛→현재):")
        for limb in ("arm", "leg"):
            for side in ("left", "right"):
                print(
                    f"      {limb:<4} {side:<5} "
                    f"{old[limb][side]:7.2f} → {new[limb][side]:7.2f}"
                    f"  ×{new[limb][side] / old[limb][side]:.2f}"
                )
            flip = old[limb]["picked"] != new[limb]["picked"]
            print(
                f"      {limb:<4} 판별 {old[limb]['picked']} → {new[limb]['picked']}"
                f"  {'**뒤집힘**' if flip else '(그대로)'}"
            )


if __name__ == "__main__":
    main()
