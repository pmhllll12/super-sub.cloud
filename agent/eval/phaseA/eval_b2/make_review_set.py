"""Step 1 — 세 selector 결과가 갈린 대상을 사람 검수 목록으로 뽑는다.

**GT나 selector 정답을 렌더에 암시하지 않는다.** 후보는 전부 같은 색·같은 굵기로
그리고 index만 표시한다 (Phase B-0 render_targets.py와 같은 규약).

사람이 입력할 수 있는 값은 세 가지뿐이다: 후보 index / none / uncertain.
selector 결과를 보고 GT를 자동 수정하는 경로는 만들지 않는다.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

# targets.py 는 **저장소 것**을 쓴다. /mnt/d 에도 사본이 있지만 그쪽은 갱신되지
# 않아 조용히 옛 동작을 한다 (2026-09-02에 실제로 겪었다 — 라벨 재매핑이
# 반영되지 않은 채 B-1/B-2가 돌았다). 데이터는 /mnt/d, 코드는 저장소다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from targets import RATIOS, enumerate_targets, load_candidates, target_key  # noqa: E402

ROOT = Path("/mnt/d/supersub-phaseA")
B1 = ROOT / "eval_b1"
OUT = ROOT / "eval_b2"
RENDER = OUT / "review_cases"
OUT.mkdir(exist_ok=True)
RENDER.mkdir(exist_ok=True)

BOX_COLOR = (255, 200, 0)
BOX_THICK = 2
MIN_W = MAX_W = 1100


def draw(frame, boxes, wh):
    img = frame.copy()
    h0, w0 = img.shape[:2]
    target = MAX_W if w0 > MAX_W else MIN_W
    interp = cv2.INTER_AREA if w0 > target else cv2.INTER_CUBIC
    img = cv2.resize(img, (target, int(h0 * target / w0)), interpolation=interp)
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
    frames = list(csv.DictReader(open(B1 / "selector_eval_frames.csv")))
    by = defaultdict(dict)
    for r in frames:
        by[(r["clip_id"], r["ratio"])][r["selector"]] = r

    targets = {target_key(t["clip_id"], t["ratio"]): t for t in enumerate_targets()}

    rows = []
    for (cid, ratio), sel in sorted(by.items()):
        b, a, B = sel["baseline"], sel["A"], sel["B"]
        picks = {b["selected_box_index"], a["selected_box_index"], B["selected_box_index"]}
        reasons = []
        if b["selected_box_index"] != a["selected_box_index"]:
            reasons.append("baseline!=A")
        if b["selected_box_index"] != B["selected_box_index"]:
            reasons.append("baseline!=B")
        if a["selected_box_index"] != B["selected_box_index"]:
            reasons.append("A!=B")
        if len(picks) == 1:
            continue
        # 전이 유형도 사유에 함께 남긴다 (있을 때만)
        if b["correct"] != "":
            cb, ca, cB = int(b["correct"]), int(a["correct"]), int(B["correct"])
            if not cb and ca: reasons.append("recovery:A")
            if not cb and cB: reasons.append("recovery:B")
            if cb and not ca: reasons.append("regression:A")
            if cb and not cB: reasons.append("regression:B")
            if not ca and cB: reasons.append("A->B recovery")
            if ca and not cB: reasons.append("A->B regression")
        rows.append({
            "clip_id": cid,
            "ratio": ratio,
            "frame": b["frame"],
            "gt_box_index": b["gt_box_index"],
            "baseline_box_index": b["selected_box_index"],
            "a_box_index": a["selected_box_index"],
            "b_box_index": B["selected_box_index"],
            "candidate_count": b["num_candidates"],
            "candidate_count_ge50": b["num_candidates_ge50"],
            "baseline_correct": b["correct"],
            "a_correct": a["correct"],
            "b_correct": B["correct"],
            "continuity": B["continuity"],
            "reason": ";".join(reasons),
            # 사람이 채울 칸 — 비워 둔다
            "human_box_index": "",
            "human_note": "",
        })

    with open(OUT / "review_cases.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"review cases: {len(rows)}  (clips {len({r['clip_id'] for r in rows})})")

    # 렌더 — 프레임 디코딩은 클립당 한 번만 한다
    from supersub_agent.pose import DEFAULT_TARGET_FPS, read_frames
    need = defaultdict(list)
    for r in rows:
        need[r["clip_id"]].append(r)
    for cid, rs in need.items():
        per_frame, wh, _ = load_candidates(cid)
        vid = ROOT / "clips" / f"{cid}.mp4"
        frames_img, _, _ = read_frames(str(vid), target_fps=DEFAULT_TARGET_FPS)
        for r in rs:
            f = int(r["frame"])
            img = draw(frames_img[f], per_frame[f], wh)
            hdr = np.zeros((30, img.shape[1], 3), np.uint8)
            cv2.putText(hdr, f"{cid}   frame {f}   ratio {float(r['ratio']):.0%}   "
                             f"candidates {len(per_frame[f])}",
                        (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            out = RENDER / f"{cid}@{r['ratio']}.jpg"
            cv2.imwrite(str(out), np.vstack([hdr, img]), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"  rendered {cid}: {len(rs)}", flush=True)
    print(f"renders -> {RENDER}")


if __name__ == "__main__":
    main()
