"""Tier 0 7건 blind 렌더 — A/B 불일치 중 기존 GT가 있는 프레임 전부.

후보는 전부 같은 색·같은 굵기, index와 검출점수만 표시한다. selector 이름·선택
결과·기존 GT는 이미지에도 폼에도 들어가지 않는다 (B-2/B-3와 동일 규약).
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
OUT = B4 / "tier0_cases"

sys.path.insert(0, str(ROOT / "labeling"))
sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from targets import load_candidates  # noqa: E402

BOX_COLOR = (255, 200, 0)
WIDTH = 1100

TIER0 = [
    ("3USSmzO001k", "0.80", 119),
    ("5-jBTNp5IQA", "0.50", 75),
    ("IeDin6oB-IY", "0.50", 75),
    ("N5zWQkoLM3M", "0.50", 75),
    ("N5zWQkoLM3M", "0.80", 119),
    ("X6dC9pu5H3k", "0.80", 107),
    ("sYl2jCqsSKo", "0.80", 119),
]


def draw(frame, boxes, wh):
    img = frame.copy()
    h0, w0 = img.shape[:2]
    interp = cv2.INTER_AREA if w0 > WIDTH else cv2.INTER_CUBIC
    img = cv2.resize(img, (WIDTH, int(h0 * WIDTH / w0)), interpolation=interp)
    s = img.shape[1] / wh[0]
    for i, (x1, y1, x2, y2, sc) in enumerate(boxes):
        p1, p2 = (int(x1 * s), int(y1 * s)), (int(x2 * s), int(y2 * s))
        cv2.rectangle(img, p1, p2, BOX_COLOR, 2, cv2.LINE_AA)
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
    for cid, ratio, f in TIER0:
        need[cid].append((ratio, f))

    form = []
    for cid, items in need.items():
        per_frame, wh, _ = load_candidates(cid)
        imgs, _, _ = read_frames(str(ROOT / "clips" / f"{cid}.mp4"), target_fps=DEFAULT_TARGET_FPS)
        for ratio, f in items:
            img = draw(imgs[f], per_frame[f], wh)
            hdr = np.zeros((30, img.shape[1], 3), np.uint8)
            cv2.putText(hdr, f"{cid}   frame {f}   ratio {float(ratio):.0%}   "
                             f"candidates {len(per_frame[f])}",
                        (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                        cv2.LINE_AA)
            name = f"{cid}@{ratio}.jpg"
            cv2.imwrite(str(OUT / name), np.vstack([hdr, img]),
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
            form.append({"clip_id": cid, "ratio": ratio, "frame": f,
                         "n_candidates": len(per_frame[f]),
                         "image": f"eval_b4/tier0_cases/{name}",
                         "ai_box_index": "", "ai_note": "", "ai_confidence": ""})
        print(f"  {cid}: {len(items)}", flush=True)

    form.sort(key=lambda r: (r["clip_id"], r["ratio"]))
    with open(B4 / "tier0_review_input.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(form[0]))
        w.writeheader()
        w.writerows(form)
    print(f"renders -> {OUT}   form -> tier0_review_input.csv ({len(form)}행)")


if __name__ == "__main__":
    main()
