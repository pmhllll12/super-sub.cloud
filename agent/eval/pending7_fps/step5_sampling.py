"""5단계 — (a) 샘플링 자체. read_frames가 어느 물리 시각을 고르는가.

프레임마다 균일한 밝기(= 원본 프레임 번호)를 넣은 합성 영상을 만들어, read_frames가
돌려준 프레임의 밝기로 **선택된 원본 인덱스를 역추적**한다. GPU·모델을 쓰지 않는다.

MJPG가 평탄 프레임 밝기를 1 낮게 재생하므로 측정값에 −1 오프셋이 있다. 두 인코딩의
목록이 **서로 같은지**만 보면 되고, 오프셋은 디코딩 원본과 대조해 확인했다.

표 16  같은 내용을 다른 fps로 인코딩했을 때 고르는 원본 인덱스
표 17  정수배가 아닌 소스 fps에서 격자가 어긋나는 것 (인접 결함 1)
표 18  max_frames=300이 덮는 실시간 길이 (인접 결함 2)
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core import WORK
from supersub_agent.pose import read_frames

OUT = WORK / "synthetic"


def make_clip(path: Path, n: int, fps: float, stride: int = 1) -> None:
    """원본 60fps 기준 인덱스를 밝기로 새긴 영상. stride>1이면 그만큼 솎아 낸다."""
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (64, 48))
    for i in range(0, n, stride):
        w.write(np.full((48, 64, 3), i % 256, dtype=np.uint8))
    w.release()


def picked(path: Path, target: int) -> tuple[list[int], float, float]:
    frames, src, sampled = read_frames(path, target_fps=target)
    return [int(round(f.mean())) for f in frames], src, sampled


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("표 16 — 같은 내용을 다른 fps로 인코딩했을 때 read_frames가 고르는 원본 인덱스")
    print("        (밝기에 60fps 기준 인덱스를 새겨 역추적. target_fps=15 고정)\n")

    results = {}
    for label, n, fps, stride in (
        ("60fps 원본", 240, 60.0, 1),
        ("30fps 판(2프레임마다)", 240, 30.0, 2),
        ("20fps 판(3프레임마다)", 240, 20.0, 3),
    ):
        p = OUT / f"clip_{int(fps)}.avi"
        make_clip(p, n, fps, stride)
        idx, src, sampled = picked(p, 15)
        results[label] = idx
        print(f"{label:<24} src={src:>5.1f}  sampled={sampled:>6.2f}  "
              f"n={len(idx):>3}  선택 물리인덱스 앞 8개 {idx[:8]}")

    a = results["60fps 원본"]
    b = results["30fps 판(2프레임마다)"]
    c = results["20fps 판(3프레임마다)"]
    m = min(len(a), len(b))
    print(f"\n  60fps vs 30fps 판 : 앞 {m}개 물리인덱스 동일  {a[:m] == b[:m]}")
    m2 = min(len(a), len(c))
    print(f"  60fps vs 20fps 판 : 앞 {m2}개 물리인덱스 동일  {a[:m2] == c[:m2]}")

    print("\n표 17 — 정수배가 아닌 소스 fps에서는 격자가 어긋난다 (target_fps=15)")
    for fps in (24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0):
        step = max(1, round(fps / 15))
        eff = fps / step
        times = [i * step / fps for i in range(4)]
        print(f"  src {fps:>6.2f}fps  step={step}  실효 {eff:>5.2f}fps  "
              f"선택 시각(초) {[round(t, 4) for t in times]}")

    print("\n표 18 — max_frames=300 절단이 덮는 실시간 길이")
    for fps in (25.0, 30.0, 50.0, 60.0, 120.0):
        step = max(1, round(fps / 15))
        eff = fps / step
        print(f"  src {fps:>6.1f}fps  실효 {eff:>5.2f}fps  "
              f"300프레임 = {300 / eff:>6.1f}초 분량")


if __name__ == "__main__":
    main()
