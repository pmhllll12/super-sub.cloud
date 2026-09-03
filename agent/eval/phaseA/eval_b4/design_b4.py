"""Phase B-4 설계 — A-pose vs B-pose를 가를 추가 검수 대상을 고른다.

**selector 구현·가중치는 eval_b2.py에서 그대로 import 한다.** 이 파일에는
selector 로직도 가중치도 없다. 라벨·B-2 산출물은 읽기만 한다.

B-2 평가 CSV는 클립당 3프레임(117개)만 담고 있으나, A-pose/B-pose가 갈리는
프레임은 클립 전 구간에 흩어져 있다. 따라서 같은 selector를 **모든 프레임**에
다시 돌려(결정론적이므로 B-2와 동일한 결과) 불일치를 전수 추출한다.
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
B4 = ROOT / "eval_b4"
B4.mkdir(exist_ok=True)

# 코드는 저장소, 데이터는 /mnt/d. /mnt/d 사본은 갱신되지 않아 조용히 옛
# 동작을 한다 (2026-09-02에 실제로 겪었다).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval_b2"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
from targets import enumerate_targets, load_candidates, target_key  # noqa: E402

import eval_b2 as e2  # noqa: E402  selector 구현·가중치의 유일한 출처

MODES = e2.MODES
SWITCH_IOU = e2.SWITCH_IOU
DIFF_PERSON_IOU = 0.30   # 두 선택이 '다른 사람'이라고 볼 상한
REGRESSION_CASES = {("LhD_fnHt_xg", "0.50"), ("LhD_fnHt_xg", "0.80"),
                    ("N5zWQkoLM3M", "0.50")}

cfg = json.loads((B2 / "eval_config.json").read_text())
for m, w in cfg["weights"].items():
    for k, v in w.items():
        assert abs(e2.WEIGHTS[m][k] - v) < 1e-12, f"가중치 불일치: {m}.{k}"


def main() -> None:
    pq = e2.load_pq()
    old = json.loads((ROOT / "labeling" / "labels.json").read_text())
    old_gt = {target_key(r["clip_id"], r["ratio"]): r["box_index"] for r in old["frames"]}
    ai = json.loads((B3 / "labels_ai_reviewed.json").read_text())
    ai_gt = {target_key(r["clip_id"], r["ratio"]): (r["ai_box_index"], r["ai_confidence"])
             for r in ai["labels"] if r["sport"] == "baseball"}

    targets = enumerate_targets()
    tgt_by_frame = {(t["clip_id"], t["frame"]): t for t in targets}
    clips = sorted({t["clip_id"] for t in targets})

    rows = []
    per_clip_frames = {}
    for cid in clips:
        per_frame, wh, _ = load_candidates(cid)
        per_clip_frames[cid] = len(per_frame)
        sels = {m: e2.run(per_frame, wh, m, cid, pq) for m in MODES}

        for t in range(len(per_frame)):
            ia, ba, fa = sels["A_pose"][t]
            ib, bb, fb = sels["B_pose"][t]
            if ia is None or ib is None or ia == ib:
                continue

            boxes_all = per_frame[t]
            n50 = int((boxes_all[:, 4] >= e2.DET_THRESHOLD).sum())
            pair_iou = e2.iou(ba, bb)

            # 각 selector가 직전 자기 선택 대비 사람을 바꿨는가 (switch)
            sw = {}
            for m in ("A_pose", "B_pose"):
                prev = sels[m][t - 1][1] if t > 0 else None
                sw[m] = "" if prev is None else int(e2.iou(prev, sels[m][t][1]) < SWITCH_IOU)

            tinfo = tgt_by_frame.get((cid, t))
            ratio = f"{tinfo['ratio']:.2f}" if tinfo else ""
            key = target_key(cid, tinfo["ratio"]) if tinfo else None
            g_old = old_gt.get(key) if key else None
            g_ai, c_ai = ai_gt.get(key, (None, None)) if key else (None, None)

            def corr(gi, pick):
                return "" if gi is None or not isinstance(gi, int) else int(pick == gi)

            areas = (boxes_all[:, 2] - boxes_all[:, 0]) * (boxes_all[:, 3] - boxes_all[:, 1])
            frac = float(min(areas[ia], areas[ib]) / (wh[0] * wh[1]))

            rows.append({
                "clip_id": cid, "frame": t, "ratio": ratio,
                "is_target": int(tinfo is not None),
                "n_candidates": len(boxes_all), "n_candidates_ge50": n50,
                "baseline_box": sels["baseline"][t][0],
                "a_pose_box": ia, "b_pose_box": ib,
                "pair_iou": round(pair_iou, 3),
                "different_person": int(pair_iou < DIFF_PERSON_IOU),
                "a_pose_pq": round(fa["pose_quality"], 3),
                "b_pose_pq": round(fb["pose_quality"], 3),
                "a_pose_cen": round(fa["centrality"], 3),
                "b_pose_cen": round(fb["centrality"], 3),
                "a_pose_size": round(fa["size"], 3),
                "b_pose_size": round(fb["size"], 3),
                "b_pose_continuity": round(fb["continuity"], 3),
                "a_pose_continuity": round(fa["continuity"], 3),
                "b_locked": int(fb["continuity"] >= 0.8),
                "a_pose_switch": sw["A_pose"], "b_pose_switch": sw["B_pose"],
                "min_box_frac": round(frac, 4),
                "gt_source": ("labels.json" if g_old is not None else
                              ("ai_reviewed" if isinstance(g_ai, int) else
                               ("ai_" + str(g_ai) if g_ai is not None else "none"))),
                "old_gt": "" if g_old is None else g_old,
                "ai_gt": "" if g_ai is None else g_ai,
                "ai_conf": c_ai or "",
                "a_correct_old": corr(g_old, ia), "b_correct_old": corr(g_old, ib),
                "a_correct_ai": corr(g_ai, ia), "b_correct_ai": corr(g_ai, ib),
                "is_regression_case": int((cid, ratio) in REGRESSION_CASES),
            })

    # ---- 연속 불일치 구간(run) 길이 --------------------------------------
    byclip = defaultdict(list)
    for r in rows:
        byclip[r["clip_id"]].append(r)
    for cid, rs in byclip.items():
        rs.sort(key=lambda r: r["frame"])
        run_id, prev_f = 0, None
        runs = defaultdict(list)
        for r in rs:
            if prev_f is None or r["frame"] != prev_f + 1:
                run_id += 1
            r["_run"] = run_id
            runs[run_id].append(r)
            prev_f = r["frame"]
        for r in rs:
            r["run_len"] = len(runs[r["_run"]])
            r.pop("_run")

    # ---- 정보량 점수 -----------------------------------------------------
    # 검수자가 '어느 쪽이 분석 대상인가'를 실제로 판별할 수 있고, 그 답이
    # A-pose/B-pose를 가르는 데 기여하는 프레임에 높은 점수를 준다.
    for r in rows:
        s = 0.0
        s += 3.0 * r["different_person"]                    # 같은 사람 미세이동은 무가치
        s += 2.0 * r["b_locked"]                            # B가 고착된 상태 = 핵심 축
        s += 1.5 * min(r["run_len"], 10) / 10.0             # 지속된 분기가 진단적
        s += 1.5 * min(r["min_box_frac"] / 0.02, 1.0)       # 너무 작으면 육안 판별 불가
        s += 1.0 * (1.0 if r["a_pose_switch"] == 1 else 0.0)  # A가 사람을 바꾼 순간
        s += 0.5 * min(r["n_candidates_ge50"], 6) / 6.0
        r["info_score"] = round(s, 3)

    rows.sort(key=lambda r: (-r["info_score"], r["clip_id"], r["frame"]))
    fields = [k for k in rows[0] if k != "info_score"] + ["info_score"]
    with open(B4 / "ab_disagreement_frames.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    total_frames = sum(per_clip_frames.values())
    labeled = [r for r in rows if r["gt_source"] in ("labels.json", "ai_reviewed")]
    print(f"clips={len(clips)} frames={total_frames} disagreements={len(rows)} "
          f"({len(rows)/total_frames:.2%})")
    print(f"  다른 사람(IoU<{DIFF_PERSON_IOU}): {sum(r['different_person'] for r in rows)}")
    print(f"  target 프레임: {sum(r['is_target'] for r in rows)}   GT 있음: {len(labeled)}")
    print(f"  클립 수: {len({r['clip_id'] for r in rows})}")


if __name__ == "__main__":
    main()
