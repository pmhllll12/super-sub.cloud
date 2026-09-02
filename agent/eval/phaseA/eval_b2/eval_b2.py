"""Step 3~6 — pose_quality를 넣은 A-pose / B-pose 평가 + continuity·centrality 분석.

가중치는 **사전에 하나로 고정**한다. 여러 조합을 돌려 최고치를 고르지 않는다
(39클립 GT에 대한 과적합이 된다). 아래 값은 Phase B-0 설계안이 제시한 원래
임시 가중치를 그대로 쓴 것이며, production 값이 아니다.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

# targets.py 는 **저장소 것**을 쓴다. /mnt/d 에도 사본이 있지만 그쪽은 갱신되지
# 않아 조용히 옛 동작을 한다 (2026-09-02에 실제로 겪었다 — 라벨 재매핑이
# 반영되지 않은 채 B-1/B-2가 돌았다). 데이터는 /mnt/d, 코드는 저장소다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
from targets import enumerate_targets, load_candidates, target_key  # noqa: E402

ROOT = Path("/mnt/d/supersub-phaseA")
OUT = ROOT / "eval_b2"

DET_THRESHOLD = 0.5
SWITCH_IOU = 0.3

# 사전 고정 가중치 — 튜닝하지 않는다.
WEIGHTS = {
    # B-1에서 쓴 것(pose_quality 제거 후 정규화). 비교 기준으로 남긴다.
    "A": {"centrality": 0.45 / 0.65, "size": 0.20 / 0.65},
    "B": {"centrality": 0.35 / 0.75, "size": 0.15 / 0.75, "continuity": 0.25 / 0.75},
    # 이번 단계의 대상 — 설계안 원안 그대로.
    "A_pose": {"centrality": 0.45, "pose_quality": 0.35, "size": 0.20},
    "B_pose": {"centrality": 0.35, "pose_quality": 0.25, "size": 0.15, "continuity": 0.25},
}
MODES = ["baseline", "A", "B", "A_pose", "B_pose"]
LABEL = {"baseline": "Baseline", "A": "A-geometry", "B": "B-geometry",
         "A_pose": "A-pose", "B_pose": "B-pose"}
KNOWN = {"3R1kvNrGJK0", "O2GSaYqH8JY", "gg5xRWjw3f8", "xMIUw5mi3Eo"}


def iou(a, b) -> float:
    if a is None or b is None:
        return 0.0
    xa, ya = max(a[0], b[0]), max(a[1], b[1])
    xb, yb = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inter / u) if u > 0 else 0.0


def geom(boxes, wh):
    W, H = wh
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    cx = (boxes[:, 0] + boxes[:, 2]) / 2.0
    cy = (boxes[:, 1] + boxes[:, 3]) / 2.0
    cen = 1.0 - np.hypot(cx - W / 2.0, cy - H / 2.0) / (0.5 * float(np.hypot(W, H)))
    size = area / area.max() if area.max() > 0 else area
    return cen, size, area


def load_pq() -> dict:
    pq = {}
    with open(OUT / "pose_quality.csv") as fh:
        for r in csv.DictReader(fh):
            pq[(r["clip_id"], int(r["frame"]), int(r["box_index"]))] = (
                float(r["pose_quality"]), int(r["valid_joint_count"])
            )
    return pq


def run(per_frame, wh, mode, cid, pq):
    out, prev = [], None
    for t, boxes_all in enumerate(per_frame):
        keep = np.where(boxes_all[:, 4] >= DET_THRESHOLD)[0]
        if len(keep) == 0:
            out.append((None, None, {})); prev = None; continue
        sub = boxes_all[keep]
        cen, size, area = geom(sub, wh)
        pqv = np.array([pq.get((cid, t, int(g)), (0.0, 0))[0] for g in keep])
        cont = (np.array([iou(prev, b[:4]) for b in sub])
                if prev is not None else np.zeros(len(sub)))
        if len(keep) == 1:
            pick = 0
        elif mode == "baseline":
            pick = int(np.argmax(area))
        else:
            w = WEIGHTS[mode]
            s = (w.get("centrality", 0) * cen + w.get("size", 0) * size
                 + w.get("pose_quality", 0) * pqv + w.get("continuity", 0) * cont)
            pick = int(np.argmax(s))
        gi = int(keep[pick]); box = boxes_all[gi, :4]
        out.append((gi, box, {"centrality": float(cen[pick]), "size": float(size[pick]),
                              "pose_quality": float(pqv[pick]), "continuity": float(cont[pick]),
                              "det_score": float(boxes_all[gi, 4])}))
        prev = box
    return out


def switch_rate(sel):
    p = [(sel[t][1], sel[t + 1][1]) for t in range(len(sel) - 1)
         if sel[t][1] is not None and sel[t + 1][1] is not None]
    return None if not p else float(np.mean([iou(a, b) < SWITCH_IOU for a, b in p]))


def main() -> None:
    pq = load_pq()
    labels = json.loads((ROOT / "labeling" / "labels.json").read_text())
    gt = {target_key(r["clip_id"], r["ratio"]): r for r in labels["frames"]}
    targets = enumerate_targets()
    by_key = {target_key(t["clip_id"], t["ratio"]): t for t in targets}
    clips = sorted({t["clip_id"] for t in targets})

    frame_rows, clip_rows, cent_rows = [], [], []
    switch = {m: {} for m in MODES}

    for cid in clips:
        per_frame, wh, _ = load_candidates(cid)
        sels = {m: run(per_frame, wh, m, cid, pq) for m in MODES}
        for m in MODES:
            switch[m][cid] = switch_rate(sels[m])

        for ratio in (0.20, 0.50, 0.80):
            k = target_key(cid, ratio)
            t, g = by_key[k], gt[k]
            f, gi = t["frame"], g["box_index"]
            boxes_all = per_frame[f]
            gt_box = boxes_all[gi, :4] if gi is not None else None
            n50 = int((boxes_all[:, 4] >= DET_THRESHOLD).sum())

            # centrality 분석용 — GT 자체의 중앙성/크기 순위
            if gi is not None and n50 > 0:
                keep = np.where(boxes_all[:, 4] >= DET_THRESHOLD)[0]
                cen, size, area = geom(boxes_all[keep], wh)
                pos = np.where(keep == gi)[0]
                cent_rows.append({
                    "clip_id": cid, "ratio": f"{ratio:.2f}", "frame": f,
                    "gt_box_index": gi, "gt_in_ge50": int(len(pos) > 0),
                    "gt_centrality": round(float(cen[pos[0]]), 3) if len(pos) else "",
                    "max_centrality": round(float(cen.max()), 3),
                    "centrality_rank": int(np.argsort(-cen).tolist().index(pos[0]) + 1) if len(pos) else "",
                    "gt_size": round(float(size[pos[0]]), 3) if len(pos) else "",
                    "size_rank": int(np.argsort(-size).tolist().index(pos[0]) + 1) if len(pos) else "",
                    "gt_pose_quality": round(pq.get((cid, f, gi), (0.0, 0))[0], 3),
                    "max_pose_quality": round(float(np.max([pq.get((cid, f, int(x)), (0.0, 0))[0] for x in keep])), 3),
                    "n_candidates_ge50": n50,
                })

            for m in MODES:
                si, sb, ft = sels[m][f]
                corr = None if gi is None else (si == gi)
                frame_rows.append({
                    "clip_id": cid, "frame": f, "ratio": f"{ratio:.2f}",
                    "gt_box_index": "" if gi is None else gi, "selector": m,
                    "selected_box_index": "" if si is None else si,
                    "selected_iou": "" if gi is None else round(iou(sb, gt_box), 3),
                    "correct": "" if corr is None else int(corr),
                    "num_candidates": t["n_candidates"], "num_candidates_ge50": n50,
                    "centrality": round(ft.get("centrality", float("nan")), 3),
                    "size": round(ft.get("size", float("nan")), 3),
                    "pose_quality": round(ft.get("pose_quality", float("nan")), 3),
                    "continuity": round(ft.get("continuity", float("nan")), 3),
                    "det_score": round(ft.get("det_score", float("nan")), 3),
                })
        for m in MODES:
            rs = [r for r in frame_rows if r["clip_id"] == cid and r["selector"] == m
                  and r["correct"] != ""]
            v, c = len(rs), sum(int(r["correct"]) for r in rs)
            clip_rows.append({
                "clip_id": cid, "selector": m, "valid_targets": v, "correct_targets": c,
                "clip_correct": "" if v == 0 else int(c >= 2),
                "single_valid_only": int(v == 1),
                "switch_rate": "" if switch[m][cid] is None else round(switch[m][cid], 4),
                "candidate_count_summary": "/".join(
                    str(by_key[target_key(cid, r)]["n_candidates"]) for r in (0.20, 0.50, 0.80)),
            })

    for name, rows in (("selector_eval_frames.csv", frame_rows),
                       ("selector_eval_clips.csv", clip_rows),
                       ("centrality_analysis.csv", cent_rows)):
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    json.dump({"weights": WEIGHTS, "det_threshold": DET_THRESHOLD,
               "switch_iou": SWITCH_IOU,
               "note": "사전 고정 가중치. 튜닝·sweep 없음. production 값 아님."},
              open(OUT / "eval_config.json", "w"), ensure_ascii=False, indent=1)
    print(f"frames={len(frame_rows)} clips={len(clip_rows)} centrality={len(cent_rows)}")


if __name__ == "__main__":
    main()
