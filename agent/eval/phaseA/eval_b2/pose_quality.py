"""Step 2 — 후보 전체에 ViTPose를 오프라인 실행해 pose_quality를 만든다.

production pose.py는 **읽기만** 한다 (모델 id·전처리 규약을 맞추기 위해).
수정하지 않고, production 실행 경로도 건드리지 않는다.

배치 규약: 프레임 하나의 후보를 **한 번의 forward로** 처리한다.
ViTPose 프로세서는 boxes=[[b1, b2, ...]] 형태로 이미지당 다중 박스를 받고
post_process는 [이미지][사람] 순으로 돌려준다 — production이 [[box]] 를 넣고
[0][0] 으로 꺼내는 구조가 그 중첩을 드러낸다.

pose_quality 정의 (eval_config.json에도 기록):
    pose_quality      = mean(17개 키포인트 신뢰도)
    valid_joint_count = count(신뢰도 >= JOINT_THRESHOLD)

**JOINT_THRESHOLD는 production 임계값이 아니다.** features.LIMB_MIN_CONFIDENCE는
사지별로 다르고(leg 0.3 / arm 0.6) 게이트 목적이 다르다. 여기서는 후보를 서로
비교하기 위한 관측용 값이며 0.3으로 고정한다.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

# targets.py 는 **저장소 것**을 쓴다. /mnt/d 에도 사본이 있지만 그쪽은 갱신되지
# 않아 조용히 옛 동작을 한다 (2026-09-02에 실제로 겪었다 — 라벨 재매핑이
# 반영되지 않은 채 B-1/B-2가 돌았다). 데이터는 /mnt/d, 코드는 저장소다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from targets import clip_ids, load_candidates  # noqa: E402

from supersub_agent.pose import DEFAULT_TARGET_FPS, POSE_MODEL, read_frames  # noqa: E402  (읽기 전용 import)

ROOT = Path("/mnt/d/supersub-phaseA")
OUT = ROOT / "eval_b2"
OUT.mkdir(exist_ok=True)

DET_THRESHOLD = 0.5          # selector가 보는 후보 집합 (production _largest_person_box와 동일)
JOINT_THRESHOLD = 0.3        # 관측용. production 임계값 아님.
MAX_BATCH = 24               # OOM 시 절반으로 줄여 재시도


def main() -> None:
    from transformers import AutoProcessor, VitPoseForPoseEstimation

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(POSE_MODEL)
    model = VitPoseForPoseEstimation.from_pretrained(POSE_MODEL).to(dev).eval()

    rows: list[dict] = []
    timings: list[dict] = []
    oom_events = 0
    t_all = time.time()

    for i, cid in enumerate(clip_ids(), 1):
        per_frame, wh, _ = load_candidates(cid)
        frames, _, _ = read_frames(str(ROOT / "clips" / f"{cid}.mp4"), target_fps=DEFAULT_TARGET_FPS)
        if len(frames) != len(per_frame):
            raise RuntimeError(f"{cid}: 프레임 {len(frames)} != 후보캐시 {len(per_frame)}")

        t0 = time.time()
        n_cand = 0
        for t, boxes_all in enumerate(per_frame):
            keep = np.where(boxes_all[:, 4] >= DET_THRESHOLD)[0]
            if len(keep) == 0:
                continue
            rgb = cv2.cvtColor(frames[t], cv2.COLOR_BGR2RGB)
            # COCO xywh — production이 _largest_person_box에서 만드는 형식과 같다
            xywh = [
                [float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])]
                for b in boxes_all[keep]
            ]
            batch = MAX_BATCH
            done = None
            while done is None:
                try:
                    outs = []
                    for s in range(0, len(xywh), batch):
                        chunk = xywh[s : s + batch]
                        inp = proc(rgb, boxes=[chunk], return_tensors="pt").to(dev)
                        with torch.inference_mode():
                            o = model(**inp)
                        outs.extend(proc.post_process_pose_estimation(o, boxes=[chunk])[0])
                    done = outs
                except torch.cuda.OutOfMemoryError:  # pragma: no cover
                    torch.cuda.empty_cache()
                    batch = max(1, batch // 2)
                    globals()["_OOM"] = globals().get("_OOM", 0) + 1
                    if batch == 1:
                        raise
            for j, gi in enumerate(keep):
                sc = np.asarray(done[j]["scores"], dtype=np.float64)
                rows.append(
                    {
                        "clip_id": cid,
                        "frame": t,
                        "box_index": int(gi),
                        "det_score": round(float(boxes_all[gi, 4]), 4),
                        "pose_quality": round(float(sc.mean()), 4),
                        "valid_joint_count": int((sc >= JOINT_THRESHOLD).sum()),
                        "low_conf_ratio": round(float((sc < JOINT_THRESHOLD).mean()), 4),
                    }
                )
                n_cand += 1
        dt = time.time() - t0
        timings.append({"clip_id": cid, "frames": len(per_frame), "candidates": n_cand,
                        "seconds": round(dt, 2),
                        "ms_per_candidate": round(1000 * dt / max(1, n_cand), 2)})
        print(f"[{i}/39] {cid} {n_cand} cands {dt:.0f}s "
              f"({1000*dt/max(1,n_cand):.0f} ms/cand)", flush=True)

    total = time.time() - t_all
    del model
    if dev == "cuda":
        torch.cuda.empty_cache()

    with open(OUT / "pose_quality.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(OUT / "pose_quality_timing.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(timings[0]))
        w.writeheader()
        w.writerows(timings)

    secs = [t["seconds"] for t in timings]
    json.dump(
        {
            "pose_quality": "mean(17 keypoint confidences) from ViTPose",
            "valid_joint_count": f"count(conf >= {JOINT_THRESHOLD})",
            "joint_threshold": JOINT_THRESHOLD,
            "joint_threshold_note": "관측용 값. production features.LIMB_MIN_CONFIDENCE(leg .3/arm .6)와 무관.",
            "det_threshold": DET_THRESHOLD,
            "model": POSE_MODEL,
            "max_batch": MAX_BATCH,
            "oom_events": globals().get("_OOM", 0),
            "total_seconds": round(total, 1),
            "clip_mean_seconds": round(float(np.mean(secs)), 1),
            "clip_median_seconds": round(float(np.median(secs)), 1),
            "total_candidates": len(rows),
        },
        open(OUT / "pose_quality_config.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    print(f"POSE QUALITY DONE  {len(rows)} rows  total {total/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
