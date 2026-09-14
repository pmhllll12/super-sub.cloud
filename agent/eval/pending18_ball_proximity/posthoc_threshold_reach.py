"""사후 관찰 ② — 단일후보 92%가 **장면의 성질인가 문턱의 성질인가**.

🔴 **판정에 안 쓴다.** 사전 등록 판정(분모 0편)은 이미 났고, 이것은 다음 회차의
방향을 정하기 위한 관측이다. 🔴 **`PERSON_ELIGIBLE_THRESHOLD` 을 바꾸지
않는다** — 여기서 재는 것은 「문턱을 안 걸면 후보가 몇이나 되는가」이지
「문턱을 낮추자」가 아니다 (43번 「하지 말 것」).

본 회차가 eligible(≥0.5) 박스만 남겨서, 문턱 아래에 무엇이 있었는지는
검출을 다시 돌려야 안다. 🔴 GPU 를 쓴다(검출만).

    cd agent && uv run python eval/pending18_ball_proximity/posthoc_threshold_reach.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.pose import (  # noqa: E402
    COCO_PERSON_LABEL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    PERSON_ELIGIBLE_THRESHOLD,
    _largest_person_box,
    _load_detector,
    _tracked_centers,
    read_frames_ex,
    stack_object_tracks,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
NEAR = 0.25
DET_FLOOR = 0.3      # post_process_object_detection 의 임계값 — production 값
BANDS = (0.3, 0.4, PERSON_ELIGIBLE_THRESHOLD, 0.6, 0.7)


def person_boxes(detections, thr: float):
    out = []
    for score, label, box in zip(detections["scores"], detections["labels"],
                                 detections["boxes"]):
        if int(label) != COCO_PERSON_LABEL or float(score) < thr:
            continue
        x1, y1, x2, y2 = [float(v) for v in box]
        out.append(((x1, y1, x2 - x1, y2 - y1), float(score)))
    return out


def foot(box):
    x, y, w, h = box
    return x + w / 2.0, y + h


def main() -> None:
    import torch

    clips = sorted(paths.soccer_clips_root().rglob("*.avi"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    det_processor, detector = _load_detector(device)
    print(f"축구 {len(clips)}편 · device={device} · "
          f"검출 바닥 {DET_FLOOR} · eligible {PERSON_ELIGIBLE_THRESHOLD}\n")

    per_clip = []
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        read = read_frames_ex(clip, DEFAULT_TARGET_FPS, None, DEFAULT_MAX_SECONDS)
        frames_boxes, obj_frames, chosen = [], [], []
        for frame in read.frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            inp = det_processor(images=rgb, return_tensors="pt").to(device)
            with torch.inference_mode():
                out = detector(**inp)
            det = det_processor.post_process_object_detection(
                out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=DET_FLOOR
            )[0]
            frames_boxes.append(person_boxes(det, DET_FLOOR))
            obj_frames.append(_tracked_centers(det))
            chosen.append(_largest_person_box(det))

        ball = stack_object_tracks(obj_frames).get("sports_ball")
        # 🔴 자는 본 회차와 **같다** — eligible(≥0.5) 박스 높이의 클립 중앙값.
        #    문턱을 바꿔 가며 재는 회차에서 자까지 함께 움직이면 비교가 안 된다.
        heights = [b[3] for f in frames_boxes for b, s in f
                   if s >= PERSON_ELIGIBLE_THRESHOLD]
        H = float(statistics.median(heights)) if heights else None
        per_clip.append({
            "clip": clip.name, "H": H,
            "counts": [[sum(1 for _, s in f if s >= t) for t in BANDS]
                       for f in frames_boxes],
            "near_owner": _near_owner(frames_boxes, chosen, ball, H),
        })
        print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} ({time.time()-t0:.1f}초)")

    (HERE / "threshold_reach_raw.json").write_text(
        json.dumps(per_clip, ensure_ascii=False), encoding="utf-8")
    report(per_clip)


def _near_owner(frames_boxes, chosen, ball, H):
    """공 발치(≤NEAR)에 있는 후보를, 문턱 밴드별로 센다.

    돌려주는 것은 프레임별 [밴드별 후보 수, 밴드별 「고른 사람이 최근접인가」]다.
    """
    if ball is None or H is None or H <= 0:
        return []
    rows = []
    for t, boxes in enumerate(frames_boxes):
        if ball[t, 2] <= 0 or chosen[t] is None:
            continue
        bx, by = ball[t, 0], ball[t, 1]
        row = {"t": t, "bands": []}
        for thr in BANDS:
            cand = [b for b, s in boxes if s >= thr]
            if not cand:
                row["bands"].append(None)
                continue
            ds = [float(np.hypot(*(np.array(foot(b)) - (bx, by))) / H) for b in cand]
            ai = int(np.argmin(ds))
            ci = int(np.argmax([b[2] * b[3] for b in cand]))
            row["bands"].append({
                "n": len(cand), "d_min": round(ds[ai], 3),
                "match": ai == ci,
                "h_ratio": round(cand[ci][3] / cand[ai][3], 2) if cand[ai][3] else None,
            })
        rows.append(row)
    return rows


def report(per_clip) -> None:
    print("\n" + "=" * 70)
    print("⑴ 사람 후보 수 — 문턱 밴드별 (프레임 전수)")
    counts = [c for clip in per_clip for c in clip["counts"]]
    print(f"     {'문턱':>6s} {'중앙':>5s} {'평균':>6s} {'≥2인 프레임':>12s}")
    for j, thr in enumerate(BANDS):
        col = [c[j] for c in counts]
        print(f"     {thr:6.2f} {statistics.median(col):5.0f} "
              f"{statistics.fmean(col):6.2f} "
              f"{sum(v >= 2 for v in col)/len(col):11.0%}")

    print("\n⑵ 공이 보이는 프레임에서 — 발치(≤%.2f 키높이)에 후보가 있는가" % NEAR)
    rows = [r for clip in per_clip for r in clip["near_owner"]]
    print(f"     공 보인 프레임 {len(rows)}개")
    print(f"     {'문턱':>6s} {'발치에 후보 있음':>16s} {'그중 후보≥2':>12s} "
          f"{'고른 사람이 최근접':>18s} {'불일치 키비':>12s}")
    for j, thr in enumerate(BANDS):
        near = [r["bands"][j] for r in rows
                if r["bands"][j] and r["bands"][j]["d_min"] <= NEAR]
        multi = [b for b in near if b["n"] >= 2]
        m = (sum(b["match"] for b in multi) / len(multi)) if multi else float("nan")
        hr = [b["h_ratio"] for b in multi if not b["match"] and b["h_ratio"]]
        print(f"     {thr:6.2f} {len(near):16d} {len(multi):12d} "
              f"{m:17.0%} "
              f"{statistics.median(hr) if hr else float('nan'):12.2f}")

    print("\n⑶ 🔴 문턱을 안 걸었을 때(0.3) 주 층이 서는가 — 다음 회차의 재료")
    j = 0
    multi = [r["bands"][j] for r in rows
             if r["bands"][j] and r["bands"][j]["d_min"] <= NEAR
             and r["bands"][j]["n"] >= 2]
    print(f"     주 층 {len(multi)}프레임 "
          f"(사전 등록 주 층은 1프레임이었다)")


if __name__ == "__main__":
    main()
