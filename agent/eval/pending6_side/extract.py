"""미결 6번 — 스윙 측 자동 판별을 재검토할 두 실클립의 포즈 덤프를 만든다.

미결 6번에 적힌 travel 수치(야구 18.2 대 27.6, 농구 16.30 대 16.09)는 실효
12.5fps / 12.0fps에서 나온 값이다. 동작점이 target 30으로 바뀌면서
(실효 25fps / 23.98fps) 그 수치를 **재계산할 방법이 없었다** — 두 클립의
키포인트가 어디에도 남아 있지 않아 확인하려면 매번 GPU가 필요했다.

이 스크립트는 production 경로 그대로(`pose.extract_keypoints`,
`target_fps=DEFAULT_TARGET_FPS`, `observe=False`) 한 번 돌려 `cache/`에 남긴다.
이후 재해석은 `recompute.py`가 CPU로 한다.

production code는 **import만** 한다. `agent/src/`를 수정하지 않는다.

    cd agent && .venv/bin/python eval/pending6_side/extract.py
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent
CACHE = HERE / "cache"

if importlib.util.find_spec("supersub_agent") is None:  # pragma: no cover
    sys.path.insert(0, str(AGENT / "src"))

from supersub_agent import pose  # noqa: E402

# 미결 6번이 근거로 든 두 클립. 세 번째(농구 점프슛 bball_shot.mp4)는 미결
# 6번의 travel 수치에 등장하지 않아 넣지 않는다.
CLIPS = ("baseball_pitch_trim", "bball_layup_trim")


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    for cid in CLIPS:
        src = AGENT / "data" / f"{cid}.mp4"
        out = CACHE / f"{cid}.npz"
        if out.exists():
            print(f"skip {cid} (이미 있음)", flush=True)
            continue
        t0 = time.time()
        # observe=False — 오프라인 조사는 서비스 입력이 아니다. 기본값이 True라
        # 그냥 두면 서비스 입력 분포에 섞인다 (extract_keypoints 참고).
        r = pose.extract_keypoints(
            str(src), target_fps=pose.DEFAULT_TARGET_FPS, observe=False
        )
        np.savez_compressed(
            out,
            keypoints=r.keypoints,
            source_fps=r.source_fps,
            sampled_fps=r.sampled_fps,
            target_fps=pose.DEFAULT_TARGET_FPS,
            **{f"obj_{k}": v for k, v in r.objects.items()},
        )
        print(
            f"{cid} {r.keypoints.shape[0]}f "
            f"src={r.source_fps:.2f} sampled={r.sampled_fps:.2f} "
            f"objs={sorted(r.objects)} {time.time() - t0:.0f}s",
            flush=True,
        )
    print("EXTRACT DONE", flush=True)


if __name__ == "__main__":
    main()
