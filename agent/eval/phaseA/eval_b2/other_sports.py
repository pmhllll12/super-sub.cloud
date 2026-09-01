"""Step 10 — 기존 종목 클립에서 selector 결과가 baseline과 달라지는 프레임을 센다.

production code는 수정하지 않는다. RT-DETR + ViTPose를 오프라인으로 돌려
baseline / A / B / A-pose / B-pose 선택을 비교만 한다.

**"선택이 달라졌다"를 곧 regression으로 부르지 않는다.** 달라진 프레임을
review 대상으로 뽑아 두고, 판단은 사람이 한다.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent.pose import (  # noqa: E402  (읽기 전용)
    COCO_PERSON_LABEL,
    PERSON_DETECTOR,
    POSE_MODEL,
    read_frames,
)

OUT = Path("/mnt/d/supersub-phaseA/eval_b2")
DET_THRESHOLD = 0.5
WEIGHTS = {
    "A": {"centrality": 0.45 / 0.65, "size": 0.20 / 0.65},
    "B": {"centrality": 0.35 / 0.75, "size": 0.15 / 0.75, "continuity": 0.25 / 0.75},
    "A_pose": {"centrality": 0.45, "pose_quality": 0.35, "size": 0.20},
    "B_pose": {"centrality": 0.35, "pose_quality": 0.25, "size": 0.15, "continuity": 0.25},
}
MODES = ["baseline", "A", "B", "A_pose", "B_pose"]


def iou(a, b):
    if a is None or b is None:
        return 0.0
    xa, ya = max(a[0], b[0]), max(a[1], b[1])
    xb, yb = min(a[2], b[2]), min(a[3], b[3])
    it = max(0.0, xb - xa) * max(0.0, yb - ya)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - it
    return float(it / u) if u > 0 else 0.0


def main() -> None:
    from transformers import AutoProcessor, RTDetrForObjectDetection, VitPoseForPoseEstimation

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dproc = AutoProcessor.from_pretrained(PERSON_DETECTOR)
    det = RTDetrForObjectDetection.from_pretrained(PERSON_DETECTOR).to(dev).eval()
    pproc = AutoProcessor.from_pretrained(POSE_MODEL)
    pose = VitPoseForPoseEstimation.from_pretrained(POSE_MODEL).to(dev).eval()

    root = Path("/home/ho/projects/super-sub.cloud/agent/data")
    vids = sorted(root.glob("*.mp4")) + sorted((root / "goldenset" / "soccerkicks_video").glob("*.avi"))
    rows, diffs = [], []

    for vi, p in enumerate(vids, 1):
        t0 = time.time()
        frames, _, _ = read_frames(str(p), target_fps=15)
        prev = {m: None for m in MODES}
        n_multi = 0
        picks_hist = {m: [] for m in MODES}
        for t, fr in enumerate(frames):
            rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            inp = dproc(images=rgb, return_tensors="pt").to(dev)
            with torch.inference_mode():
                o = det(**inp)
            d = dproc.post_process_object_detection(
                o, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3)[0]
            boxes = np.array([[float(v) for v in b] + [float(s)]
                              for s, l, b in zip(d["scores"], d["labels"], d["boxes"])
                              if int(l) == COCO_PERSON_LABEL and float(s) >= DET_THRESHOLD]) \
                if len(d["scores"]) else np.zeros((0, 5))
            if len(boxes) == 0:
                for m in MODES:
                    picks_hist[m].append(None); prev[m] = None
                continue
            if len(boxes) >= 2:
                n_multi += 1
            H, W = rgb.shape[:2]
            area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            cx = (boxes[:, 0] + boxes[:, 2]) / 2; cy = (boxes[:, 1] + boxes[:, 3]) / 2
            cen = 1 - np.hypot(cx - W / 2, cy - H / 2) / (0.5 * float(np.hypot(W, H)))
            size = area / area.max()
            xywh = [[float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])] for b in boxes]
            pin = pproc(rgb, boxes=[xywh], return_tensors="pt").to(dev)
            with torch.inference_mode():
                po = pose(**pin)
            pres = pproc.post_process_pose_estimation(po, boxes=[xywh])[0]
            pq = np.array([float(np.asarray(r["scores"]).mean()) for r in pres])
            sel = {}
            for m in MODES:
                if len(boxes) == 1:
                    j = 0
                elif m == "baseline":
                    j = int(np.argmax(area))
                else:
                    w = WEIGHTS[m]
                    cont = (np.array([iou(prev[m], b[:4]) for b in boxes])
                            if prev[m] is not None else np.zeros(len(boxes)))
                    s = (w.get("centrality", 0) * cen + w.get("size", 0) * size
                         + w.get("pose_quality", 0) * pq + w.get("continuity", 0) * cont)
                    j = int(np.argmax(s))
                sel[m] = j
                picks_hist[m].append(j)
                prev[m] = boxes[j, :4]
            for m in MODES[1:]:
                if sel[m] != sel["baseline"]:
                    diffs.append({"video": p.name, "frame": t, "selector": m,
                                  "baseline_box": sel["baseline"], "selector_box": sel[m],
                                  "n_candidates": len(boxes),
                                  "iou_vs_baseline": round(iou(boxes[sel["baseline"], :4],
                                                               boxes[sel[m], :4]), 3)})
        changed = {m: sum(1 for a, b in zip(picks_hist["baseline"], picks_hist[m])
                          if a != b) for m in MODES[1:]}
        rows.append({"video": p.name, "frames": len(frames), "multi_cand_frames": n_multi,
                     **{f"changed_{m}": changed[m] for m in MODES[1:]},
                     "seconds": round(time.time() - t0, 1)})
        print(f"[{vi}/{len(vids)}] {p.name:26s} {len(frames):3d}f multi={n_multi:3d} "
              f"changed={changed}", flush=True)

    with open(OUT / "other_sports_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    if diffs:
        with open(OUT / "other_sports_diffs.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(diffs[0])); w.writeheader(); w.writerows(diffs)
    tot = {m: sum(r[f"changed_{m}"] for r in rows) for m in MODES[1:]}
    tf = sum(r["frames"] for r in rows); tm = sum(r["multi_cand_frames"] for r in rows)
    print(f"\nOTHER SPORTS DONE  영상 {len(rows)}개  총 {tf}프레임  다인 {tm}프레임")
    for m in MODES[1:]:
        print(f"  {m:8s} baseline과 다른 프레임 {tot[m]}  ({tot[m]/tf:.2%} of frames)")


if __name__ == "__main__":
    main()
