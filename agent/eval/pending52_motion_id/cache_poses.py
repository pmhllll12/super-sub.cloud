"""클립별 키포인트·공 궤적을 **한 번만** 뽑아 캐시에 둔다 (미결 `ho` 52번 2회차).

🔴 **1회차의 진짜 병목은 분류기가 아니라 반복 비용이었다.** 확인할 것이 하나
생길 때마다 GPU 로 30분을 다시 썼다. 포즈는 결정론적이라 같은 영상·같은
`target_fps` 면 같은 값이 나오는데도 매번 다시 뽑은 것이다.

이 스크립트를 한 번 돌리면 이후 진단(`diagnose_impact.py` 등)은 **GPU 없이
초 단위**로 돈다.

    cd agent && uv run python eval/pending52_motion_id/cache_poses.py

이미 캐시가 있는 클립은 건너뛴다. 다시 뽑으려면 `--force`.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.pose import extract_keypoints  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
CLIPS = paths.motion_id_root()
CACHE = paths.motion_id_cache()

# 🔴 1회차와 **같은 값**이어야 한다 — 다르면 캐시가 그때 결과를 재현하지 못한다.
MAX_SECONDS = 40.0


def cache_path(label: str, clip_id: str) -> Path:
    return CACHE / label / f"{clip_id}.npz"


def cache_one(video: Path, out: Path) -> dict:
    """한 클립을 뽑아 npz 로 저장. 실패하면 사유를 npz 에 같이 적는다.

    🔴 **실패도 캐시한다.** 안 그러면 다음 실행이 **못 여는 영상을 또 열어 본다** —
    1회차에서 AV1 4편이 매번 같은 자리에서 죽었다.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        pose = extract_keypoints(video, observe=False, max_seconds=MAX_SECONDS)
    except Exception as exc:                        # noqa: BLE001
        np.savez_compressed(out, error=f"{type(exc).__name__}: {exc}")
        return {"ok": False, "why": f"{type(exc).__name__}: {exc}"}

    ball = (pose.objects or {}).get("sports_ball")
    np.savez_compressed(
        out,
        keypoints=pose.keypoints.astype(np.float32),
        # 공이 없으면 빈 배열을 넣는다 — 「없음」과 「안 뽑았음」을 가른다.
        ball=(ball.astype(np.float32) if ball is not None
              else np.zeros((0, 3), dtype=np.float32)),
        source_fps=float(pose.source_fps),
        sampled_fps=float(pose.sampled_fps),
        target_fps=int(pose.target_fps),
        max_seconds=float(MAX_SECONDS),
        truncated=bool(pose.truncated),
        error="",
    )
    return {"ok": True, "frames": int(len(pose.keypoints)),
            "fps": float(pose.sampled_fps),
            "ball": ball is not None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="이미 있는 캐시도 다시 뽑는다")
    args = ap.parse_args()

    manifest = list(csv.DictReader(
        (HERE / "clips_manifest.csv").open(encoding="utf-8")))
    print(f"클립 {len(manifest)}편 · 캐시 {CACHE}\n", flush=True)

    made = skipped = failed = 0
    t0 = time.time()
    for i, m in enumerate(manifest, 1):
        video = CLIPS / m["path"]
        out = cache_path(m["label"], m["id"])
        if out.exists() and not args.force:
            skipped += 1
            print(f"[{i}/{len(manifest)}] · 이미 있음 {m['id']}", flush=True)
            continue
        if not video.exists():
            print(f"[{i}/{len(manifest)}] ⊘ 영상 없음 {m['path']}", flush=True)
            continue
        r = cache_one(video, out)
        if r["ok"]:
            made += 1
            print(f"[{i}/{len(manifest)}] ✅ {m['id']} "
                  f"{r['frames']}프레임 {r['fps']:.1f}fps "
                  f"공{'○' if r['ball'] else '×'}", flush=True)
        else:
            failed += 1
            print(f"[{i}/{len(manifest)}] ❌ {m['id']} {r['why'][:60]}", flush=True)

    print(f"\n새로 뜬 것 {made} · 건너뜀 {skipped} · 실패 {failed} "
          f"· {time.time() - t0:.0f}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
