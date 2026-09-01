"""사람 후보 통계 — RT-DETR만 돌려 프레임별 person 박스를 전부 기록한다.

production pose.py의 검출 설정을 그대로 복제한다 (threshold 0.3 post-process,
_largest_person_box는 score>=0.5). 코드는 수정하지 않는다.
"""
import sys, json, time
from pathlib import Path
import numpy as np, cv2, torch
from transformers import AutoProcessor, RTDetrForObjectDetection

sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import pose as P

ROOT = Path("/mnt/d/supersub-phaseA")
OUT = ROOT/"candidates"; OUT.mkdir(exist_ok=True)
dev = "cuda" if torch.cuda.is_available() else "cpu"
proc = AutoProcessor.from_pretrained(P.PERSON_DETECTOR)
det = RTDetrForObjectDetection.from_pretrained(P.PERSON_DETECTOR).to(dev).eval()

for i, p in enumerate(sorted((ROOT/"clips").glob("*.mp4")), 1):
    cid = p.stem
    f = OUT/f"{cid}.npz"
    if f.exists(): print(f"[{i}] skip {cid}", flush=True); continue
    t0 = time.time()
    frames, src_fps, sfps = P.read_frames(str(p), target_fps=15)
    per_frame, tools = [], []
    for fr in frames:
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        inp = proc(images=rgb, return_tensors="pt").to(dev)
        with torch.inference_mode(): o = det(**inp)
        d = proc.post_process_object_detection(
            o, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3)[0]
        ps = []
        for s, l, b in zip(d["scores"], d["labels"], d["boxes"]):
            if int(l) != P.COCO_PERSON_LABEL: continue
            x1,y1,x2,y2 = [float(v) for v in b]
            ps.append([x1,y1,x2,y2,float(s)])
        per_frame.append(np.array(ps, dtype=np.float32) if ps else np.zeros((0,5),np.float32))
        tools.append(P._tracked_centers(d))
    h, w = frames[0].shape[:2]
    np.savez_compressed(f, frame_wh=np.array([w,h]), sampled_fps=sfps,
        n=np.array([len(x) for x in per_frame]),
        boxes=np.concatenate(per_frame) if per_frame else np.zeros((0,5),np.float32))
    (OUT/f"{cid}.tools.json").write_text(json.dumps(
        [{k:list(v) for k,v in t.items()} for t in tools]))
    print(f"[{i}] {cid} {len(frames)}f  후보/프레임 med "
          f"{np.median([len(x) for x in per_frame]):.0f}  {time.time()-t0:.0f}s", flush=True)
print("CANDIDATES DONE", flush=True)
