"""Phase B-3 — AI-reviewed(사람 미검증) 라벨로 동일 조건 재평가.

**selector 구현과 가중치는 eval_b2.py에서 그대로 import 한다.** 이 파일에는
selector 로직도 가중치 상수도 없다. sweep·재튜닝 경로는 존재하지 않는다.

GT 취급:
    candidate index -> 해당 후보를 GT로 사용
    none            -> GT 없음 (correct 공란, 정확도 집계에서 제외)
    uncertain       -> 평가에서 완전히 제외 (행 자체를 만들지 않는다)

B-2와의 비교를 위해 **같은 33프레임**에 대해 기존 labels.json 기준 결과도
함께 집계한다(matched subset). 표본이 달라 생기는 차이와 라벨이 달라 생기는
차이를 섞지 않기 위해서다.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
B2 = ROOT / "eval_b2"
B3 = ROOT / "eval_b3"

# 코드는 저장소, 데이터는 /mnt/d. /mnt/d 사본은 갱신되지 않아 조용히 옛
# 동작을 한다 (2026-09-02에 실제로 겪었다).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval_b2"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
from targets import enumerate_targets, load_candidates, target_key  # noqa: E402

import eval_b2 as e2  # noqa: E402  selector 구현·가중치의 유일한 출처

MODES = e2.MODES
LABEL = e2.LABEL

# 가중치가 B-2가 기록해 둔 설정과 같은지 확인한다. 다르면 즉시 중단.
cfg = json.loads((B2 / "eval_config.json").read_text())
assert cfg["det_threshold"] == e2.DET_THRESHOLD, "det_threshold 불일치"
assert cfg["switch_iou"] == e2.SWITCH_IOU, "switch_iou 불일치"
for m, w in cfg["weights"].items():
    for k, v in w.items():
        assert abs(e2.WEIGHTS[m][k] - v) < 1e-12, f"가중치 불일치: {m}.{k}"


def load_ai_labels() -> tuple[dict, dict]:
    doc = json.loads((B3 / "labels_ai_reviewed.json").read_text())
    p = doc["provenance"]
    assert p["label_source"] == "claude_visual_review"
    assert p["human_verified"] is False
    assert p["selector_blinded"] is True
    assert p["source_labels_modified"] is False
    gt, conf = {}, {}
    for r in doc["labels"]:
        if r["sport"] != "baseball":
            continue
        k = target_key(r["clip_id"], r["ratio"])
        gt[k] = r["ai_box_index"]  # int | "none" | "uncertain"
        conf[k] = r["ai_confidence"]
    return gt, conf


def main() -> None:
    pq = e2.load_pq()
    ai_gt, ai_conf = load_ai_labels()
    old = json.loads((ROOT / "labeling" / "labels.json").read_text())
    old_gt = {target_key(r["clip_id"], r["ratio"]): r["box_index"] for r in old["frames"]}

    by_key = {target_key(t["clip_id"], t["ratio"]): t for t in enumerate_targets()}
    clips = sorted({k.split("@")[0] for k in ai_gt})

    frame_rows, clip_rows, change_rows = [], [], []
    switch = {m: {} for m in MODES}

    for cid in clips:
        per_frame, wh, _ = load_candidates(cid)
        sels = {m: e2.run(per_frame, wh, m, cid, pq) for m in MODES}
        for m in MODES:
            switch[m][cid] = e2.switch_rate(sels[m])

        for ratio in (0.20, 0.50, 0.80):
            k = target_key(cid, ratio)
            if k not in ai_gt:
                continue  # AI review 대상이 아닌 프레임
            t = by_key[k]
            f = t["frame"]
            v = ai_gt[k]
            o = old_gt.get(k)

            change_rows.append({
                "clip_id": cid, "ratio": f"{ratio:.2f}", "frame": f,
                "old_box_index": "" if o is None else o,
                "ai_box_index": v,
                "ai_confidence": ai_conf[k],
                "n_candidates": t["n_candidates"],
                "change_type": (
                    "unchanged" if isinstance(v, int) and o == v else
                    "candidate->candidate" if isinstance(v, int) and o is not None else
                    "none->candidate" if isinstance(v, int) and o is None else
                    "label->none" if v == "none" and o is not None else
                    "none->none" if v == "none" else
                    "label->uncertain" if o is not None else "none->uncertain"
                ),
            })

            if v == "uncertain":
                continue  # 평가에서 제외

            gi = v if isinstance(v, int) else None  # none -> GT 없음
            boxes_all = per_frame[f]
            gt_box = boxes_all[gi, :4] if gi is not None else None
            n50 = int((boxes_all[:, 4] >= e2.DET_THRESHOLD).sum())

            for m in MODES:
                si, sb, ft = sels[m][f]
                corr = None if gi is None else (si == gi)
                old_corr = None if o is None else (si == o)
                frame_rows.append({
                    "clip_id": cid, "frame": f, "ratio": f"{ratio:.2f}",
                    "gt_source": "claude_visual_review", "human_verified": 0,
                    "gt_box_index": "" if gi is None else gi,
                    "ai_confidence": ai_conf[k],
                    "old_gt_box_index": "" if o is None else o,
                    "selector": m,
                    "selected_box_index": "" if si is None else si,
                    "selected_iou": "" if gi is None else round(e2.iou(sb, gt_box), 3),
                    "correct": "" if corr is None else int(corr),
                    "correct_vs_old_gt": "" if old_corr is None else int(old_corr),
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
            v_, c_ = len(rs), sum(int(r["correct"]) for r in rs)
            if v_ == 0:
                continue
            clip_rows.append({
                "clip_id": cid, "selector": m, "valid_targets": v_, "correct_targets": c_,
                "clip_correct": int(c_ >= 2) if v_ >= 2 else "",
                "clip_correct_all": int(c_ == v_),
                "single_valid_only": int(v_ == 1),
                "switch_rate": "" if switch[m][cid] is None else round(switch[m][cid], 4),
                "reviewed_ratios": "/".join(
                    r["ratio"] for r in frame_rows
                    if r["clip_id"] == cid and r["selector"] == m),
            })

    # ---- 전이 (AI-reviewed GT 기준) -------------------------------------
    by = defaultdict(dict)
    for r in frame_rows:
        by[(r["clip_id"], r["ratio"])][r["selector"]] = r
    pairs = [("baseline", "A"), ("baseline", "B"), ("baseline", "A_pose"),
             ("baseline", "B_pose"), ("A", "A_pose"), ("B", "B_pose"),
             ("A_pose", "B_pose"), ("A", "B")]
    trans = []
    for src, dst in pairs:
        for k, row in by.items():
            if row[src]["correct"] == "":
                continue
            cs, cd = int(row[src]["correct"]), int(row[dst]["correct"])
            if cs == cd:
                continue
            trans.append({
                "transition": f"{src}->{dst}",
                "type": "recovery" if cd else "regression",
                "clip_id": k[0], "ratio": k[1], "frame": row[dst]["frame"],
                "gt_box_index": row[src]["gt_box_index"],
                "ai_confidence": row[src]["ai_confidence"],
                "src_box": row[src]["selected_box_index"],
                "dst_box": row[dst]["selected_box_index"],
                "num_candidates": row[dst]["num_candidates"],
                "num_candidates_ge50": row[dst]["num_candidates_ge50"],
                "dst_centrality": row[dst]["centrality"], "dst_size": row[dst]["size"],
                "dst_pose_quality": row[dst]["pose_quality"],
                "dst_continuity": row[dst]["continuity"],
            })

    for name, rows in (("selector_eval_frames_ai_reviewed.csv", frame_rows),
                       ("selector_eval_clips_ai_reviewed.csv", clip_rows),
                       ("selector_eval_transitions_ai_reviewed.csv", trans),
                       ("label_change_analysis.csv", change_rows)):
        with open(B3 / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    n_eval = len({(r["clip_id"], r["ratio"]) for r in frame_rows})
    n_valid = len([r for r in frame_rows if r["selector"] == "baseline" and r["correct"] != ""])
    print(f"평가 프레임 {n_eval}  (valid GT {n_valid})  rows={len(frame_rows)}  "
          f"clips={len(clip_rows)}  transitions={len(trans)}  changes={len(change_rows)}")


if __name__ == "__main__":
    main()
