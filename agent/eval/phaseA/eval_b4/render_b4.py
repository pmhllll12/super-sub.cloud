"""B-4 blind 검수 이미지 렌더 — **아직 실행하지 않았다.**

검수 규모(N)를 확정한 뒤 select_b4.py를 다시 돌리고 이 스크립트를 실행한다.
후보는 전부 같은 색·같은 굵기로 그리고 index와 검출점수만 표시한다
(B-2 make_review_set.py / B-3와 동일 규약). selector가 무엇을 골랐는지는
이미지에도 b4_review_input.csv에도 들어가지 않는다.

    uv run python /mnt/d/supersub-phaseA/eval_b4/render_b4.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
B4 = ROOT / "eval_b4"
OUT = B4 / "review_cases"

# 코드는 저장소, 데이터는 /mnt/d. /mnt/d 사본은 갱신되지 않아 조용히 옛
# 동작을 한다 (2026-09-02에 실제로 겪었다).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from targets import load_candidates  # noqa: E402

BOX_COLOR = (255, 200, 0)
BOX_THICK = 2
WIDTH = 1100


def draw(frame, boxes, wh):
    img = frame.copy()
    h0, w0 = img.shape[:2]
    interp = cv2.INTER_AREA if w0 > WIDTH else cv2.INTER_CUBIC
    img = cv2.resize(img, (WIDTH, int(h0 * WIDTH / w0)), interpolation=interp)
    s = img.shape[1] / wh[0]
    for i, (x1, y1, x2, y2, sc) in enumerate(boxes):
        p1 = (int(x1 * s), int(y1 * s))
        p2 = (int(x2 * s), int(y2 * s))
        cv2.rectangle(img, p1, p2, BOX_COLOR, BOX_THICK, cv2.LINE_AA)
        lab = f"{i}  {sc:.2f}"
        (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        ty = p1[1] - 4 if p1[1] - th - 8 >= 0 else p1[1] + th + 6
        cv2.rectangle(img, (p1[0], ty - th - 4), (p1[0] + tw + 8, ty + 4), (0, 0, 0), -1)
        cv2.rectangle(img, (p1[0], ty - th - 4), (p1[0] + tw + 8, ty + 4), BOX_COLOR, 1)
        cv2.putText(img, lab, (p1[0] + 4, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
    return img


def main() -> None:
    from supersub_agent.pose import DEFAULT_TARGET_FPS, read_frames

    OUT.mkdir(exist_ok=True)
    need = defaultdict(list)
    for r in csv.DictReader(open(B4 / "b4_review_input.csv")):
        need[r["clip_id"]].append(int(r["frame"]))

    for cid, frames_wanted in need.items():
        per_frame, wh, _ = load_candidates(cid)
        imgs, _, _ = read_frames(str(ROOT / "clips" / f"{cid}.mp4"), target_fps=DEFAULT_TARGET_FPS)
        for f in sorted(frames_wanted):
            img = draw(imgs[f], per_frame[f], wh)
            hdr = np.zeros((30, img.shape[1], 3), np.uint8)
            cv2.putText(hdr, f"{cid}   frame {f}   candidates {len(per_frame[f])}",
                        (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                        cv2.LINE_AA)
            cv2.imwrite(str(OUT / f"{cid}@f{f:03d}.jpg"),
                        np.vstack([hdr, img]), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"  {cid}: {len(frames_wanted)}", flush=True)
    print(f"renders -> {OUT}")


if __name__ == "__main__":
    main()
