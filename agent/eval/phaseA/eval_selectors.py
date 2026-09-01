"""Phase B-1 — Baseline / A-geometry / B-geometry의 wrong-person rate 오프라인 평가.

production code는 **읽지도 import하지도 않는다** (규칙 복제만 한다). GPU·ViTPose를
쓰지 않고 Phase A가 남긴 후보 캐시와 Phase B-0 라벨만 사용한다.

selector가 보는 후보 집합은 production `_largest_person_box`와 같은 **score >= 0.5**
부분집합이다. 반면 GT의 box_index는 저장 배열 전체(score >= 0.3) 기준이므로,
selector 선택을 전체 배열 인덱스로 되돌려 비교한다.

pose_quality 항은 이번 단계에서 **산출할 수 없다**(ViTPose 재실행 금지). 지시서대로
그 항을 빼고 남은 항의 상대 가중치를 정규화해 쓴다 — production 가중치가 아니다.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/mnt/d/supersub-phaseA/labeling")
from targets import enumerate_targets, load_candidates, target_key  # noqa: E402

ROOT = Path("/mnt/d/supersub-phaseA")
OUT = ROOT / "eval_b1"
OUT.mkdir(exist_ok=True)

DET_THRESHOLD = 0.5        # production _largest_person_box와 동일
SWITCH_IOU = 0.3           # identity switching 판정
MATCH_IOU = 0.5            # 보조 지표

# pose_quality(0.35 / 0.25)를 뺀 뒤 남은 항을 정규화한 값. **임시값이다.**
W_A = {"centrality": 0.45 / 0.65, "size": 0.20 / 0.65}
W_B = {"centrality": 0.35 / 0.75, "size": 0.15 / 0.75, "continuity": 0.25 / 0.75}

KNOWN_CLIPS = ["3R1kvNrGJK0", "O2GSaYqH8JY", "gg5xRWjw3f8", "xMIUw5mi3Eo"]


def iou(a, b) -> float:
    if a is None or b is None:
        return 0.0
    xa, ya = max(a[0], b[0]), max(a[1], b[1])
    xb, yb = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inter / union) if union > 0 else 0.0


def features(boxes: np.ndarray, wh: tuple[int, int]) -> dict[str, np.ndarray]:
    """centrality / size — 검출 결과만으로 프레임 시점에 계산 가능한 항."""
    W, H = wh
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    cx = (boxes[:, 0] + boxes[:, 2]) / 2.0
    cy = (boxes[:, 1] + boxes[:, 3]) / 2.0
    diag = float(np.hypot(W, H))
    centrality = 1.0 - np.hypot(cx - W / 2.0, cy - H / 2.0) / (0.5 * diag)
    size = area / area.max() if area.max() > 0 else area
    return {"centrality": centrality, "size": size, "area": area}


def run_selector(per_frame, wh, mode: str):
    """클립 전체를 훑으며 프레임별 선택을 낸다.

    반환: (선택한 전체배열 인덱스 or None, 선택 박스 or None, 특징 dict) 리스트.
    후보 0개 -> None (production이 zeros((17,3))으로 채우는 자리와 같다)
    후보 1개 -> 그 후보 (baseline과 비트 동일한 fallback)
    """
    out = []
    prev_box = None
    for boxes_all in per_frame:
        keep = np.where(boxes_all[:, 4] >= DET_THRESHOLD)[0]
        if len(keep) == 0:
            out.append((None, None, {}))
            # 선택이 끊긴 구간에서는 연속성 기준도 끊는다.
            prev_box = None
            continue
        sub = boxes_all[keep]
        if len(keep) == 1:
            pick_local = 0
        else:
            f = features(sub, wh)
            if mode == "baseline":
                score = f["area"]
            elif mode == "A":
                score = W_A["centrality"] * f["centrality"] + W_A["size"] * f["size"]
            elif mode == "B":
                cont = (
                    np.array([iou(prev_box, b[:4]) for b in sub])
                    if prev_box is not None
                    else np.zeros(len(sub))
                )
                score = (
                    W_B["centrality"] * f["centrality"]
                    + W_B["size"] * f["size"]
                    + W_B["continuity"] * cont
                )
            else:
                raise ValueError(mode)
            pick_local = int(np.argmax(score))

        gi = int(keep[pick_local])
        box = boxes_all[gi, :4]
        f = features(sub, wh)
        cont_val = iou(prev_box, box) if prev_box is not None else 0.0
        out.append(
            (
                gi,
                box,
                {
                    "centrality": float(f["centrality"][pick_local]),
                    "size": float(f["size"][pick_local]),
                    "continuity": float(cont_val),
                    "det_score": float(boxes_all[gi, 4]),
                },
            )
        )
        prev_box = box
    return out


def switch_rate(selection) -> float | None:
    pairs = [
        (selection[t][1], selection[t + 1][1])
        for t in range(len(selection) - 1)
        if selection[t][1] is not None and selection[t + 1][1] is not None
    ]
    if not pairs:
        return None
    return float(np.mean([iou(a, b) < SWITCH_IOU for a, b in pairs]))


def main() -> None:
    labels = json.loads((ROOT / "labeling" / "labels.json").read_text())
    gt = {target_key(r["clip_id"], r["ratio"]): r for r in labels["frames"]}
    targets = enumerate_targets()
    by_key = {target_key(t["clip_id"], t["ratio"]): t for t in targets}
    clips = sorted({t["clip_id"] for t in targets})
    modes = ["baseline", "A", "B"]

    frame_rows: list[dict] = []
    clip_rows: list[dict] = []
    switch: dict[str, dict[str, float | None]] = {m: {} for m in modes}

    for cid in clips:
        per_frame, wh, _ = load_candidates(cid)
        sels = {m: run_selector(per_frame, wh, m) for m in modes}
        for m in modes:
            switch[m][cid] = switch_rate(sels[m])

        for ratio in (0.20, 0.50, 0.80):
            key = target_key(cid, ratio)
            t, g = by_key[key], gt[key]
            f = t["frame"]
            boxes_all = per_frame[f]
            gi = g["box_index"]
            gt_box = boxes_all[gi, :4] if gi is not None else None
            n50 = int((boxes_all[:, 4] >= DET_THRESHOLD).sum())
            for m in modes:
                sel_idx, sel_box, feat = sels[m][f]
                correct = None if gi is None else (sel_idx == gi)
                frame_rows.append(
                    {
                        "clip_id": cid,
                        "frame": f,
                        "ratio": f"{ratio:.2f}",
                        "gt_box_index": "" if gi is None else gi,
                        "selector": m,
                        "selected_box_index": "" if sel_idx is None else sel_idx,
                        "selected_iou": "" if gi is None else round(iou(sel_box, gt_box), 3),
                        "correct": "" if correct is None else int(correct),
                        "num_candidates": t["n_candidates"],
                        "num_candidates_ge50": n50,
                        "centrality": round(feat.get("centrality", float("nan")), 3),
                        "size": round(feat.get("size", float("nan")), 3),
                        "continuity": round(feat.get("continuity", float("nan")), 3),
                        "det_score": round(feat.get("det_score", float("nan")), 3),
                    }
                )

        for m in modes:
            rows = [
                r for r in frame_rows
                if r["clip_id"] == cid and r["selector"] == m and r["correct"] != ""
            ]
            valid = len(rows)
            corr = sum(int(r["correct"]) for r in rows)
            clip_rows.append(
                {
                    "clip_id": cid,
                    "selector": m,
                    "valid_targets": valid,
                    "correct_targets": corr,
                    # 기존 정의: valid 프레임 중 2개 이상 맞으면 correct
                    "clip_correct": "" if valid == 0 else int(corr >= 2),
                    "single_valid_only": int(valid == 1),
                    "switch_rate": "" if switch[m][cid] is None else round(switch[m][cid], 4),
                    "candidate_count_summary": "/".join(
                        str(by_key[target_key(cid, r)]["n_candidates"]) for r in (0.20, 0.50, 0.80)
                    ),
                }
            )

    with open(OUT / "selector_eval_frames.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(frame_rows[0]))
        w.writeheader()
        w.writerows(frame_rows)
    with open(OUT / "selector_eval_clips.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(clip_rows[0]))
        w.writeheader()
        w.writerows(clip_rows)

    json.dump(
        {
            "weights_note": "pose_quality 항 제거 후 정규화한 임시 가중치. production 값 아님.",
            "W_A": W_A,
            "W_B": W_B,
            "det_threshold": DET_THRESHOLD,
        },
        open(OUT / "eval_config.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    print(f"frames={len(frame_rows)}  clips={len(clip_rows)}  -> {OUT}")


if __name__ == "__main__":
    main()
