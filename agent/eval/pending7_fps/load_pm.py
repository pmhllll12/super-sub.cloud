"""PitcherMotion CSV → 클립별 (T,17,3) 배열 캐시. 표준 라이브러리 + numpy만 쓴다.

`agent/data/goldenset/pitchermotion/Pitcher_Motion_Data.csv`를 읽어
`agent/data/pending7_fps/pm_clips.npz`를 만든다. 둘 다 .gitignore 대상이다.

  V1~V51 = COCO-17 × (x, y, 신뢰도) 순서 (기하 검증 통과, 2026-08-26).
  README의 `720 - y` 안내는 적용하지 않는다 — 원본이 이미 이미지 좌표계다.
  pitch_id는 투수 안에서만 유일하므로 pitcher와 묶어야 클립 키가 된다.

읽기 전용. production code는 건드리지 않는다.
"""
from __future__ import annotations

import csv
import sys

import numpy as np

from core import CLIPS_NPZ, PM_CSV, WORK

MIN_FRAMES = 40


def main(limit_clips: int = 400) -> None:
    if not PM_CSV.exists():
        raise SystemExit(f"골든셋 CSV가 없다: {PM_CSV}")
    WORK.mkdir(parents=True, exist_ok=True)

    with PM_CSV.open(newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        idx = {name: i for i, name in enumerate(header)}
        kp_idx = [idx[f"V{i}"] for i in range(1, 52)]
        pid_i, fn_i, pit_i = idx["pitch_id"], idx["frame_num"], idx["pitcher"]

        arrays: dict[str, np.ndarray] = {}
        cur_pid: str | None = None
        buf: list[tuple[int, list[float]]] = []

        def flush() -> None:
            if cur_pid is None or len(buf) < MIN_FRAMES:
                return
            buf.sort(key=lambda r: r[0])
            arrays[cur_pid] = np.array(
                [r[1] for r in buf], dtype=np.float64
            ).reshape(len(buf), 17, 3)

        for row in rd:
            pid = f"{row[pit_i]}#{row[pid_i]}"
            if pid != cur_pid:
                flush()
                if len(arrays) >= limit_clips:
                    break
                cur_pid, buf = pid, []
            buf.append((int(float(row[fn_i])), [float(row[j]) for j in kp_idx]))
        else:
            flush()

    lens = [len(v) for v in arrays.values()]
    print(f"cached {len(arrays)} clips; frames min/med/max = "
          f"{min(lens)}/{int(np.median(lens))}/{max(lens)}", flush=True)
    np.savez_compressed(CLIPS_NPZ, **arrays)
    print(f"→ {CLIPS_NPZ}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
