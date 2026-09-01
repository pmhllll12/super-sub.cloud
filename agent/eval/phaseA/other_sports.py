"""기존 종목 샘플 클립의 사람 후보 구조 — selector 교체 시 회귀 위험 평가."""
import sys
from pathlib import Path
import numpy as np, cv2, torch
from transformers import AutoProcessor, RTDetrForObjectDetection
sys.path.insert(0,"/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import pose as P
dev="cuda" if torch.cuda.is_available() else "cpu"
proc=AutoProcessor.from_pretrained(P.PERSON_DETECTOR)
det=RTDetrForObjectDetection.from_pretrained(P.PERSON_DETECTOR).to(dev).eval()
for p in sorted(Path("/home/ho/projects/super-sub.cloud/agent/data").glob("*.mp4")):
    frames,src,sf=P.read_frames(str(p),target_fps=15)
    cnt=[];agree=[];ious=[];prev=None
    for fr in frames:
        rgb=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)
        inp=proc(images=rgb,return_tensors="pt").to(dev)
        with torch.inference_mode(): o=det(**inp)
        d=proc.post_process_object_detection(o,target_sizes=[(rgb.shape[0],rgb.shape[1])],threshold=0.3)[0]
        ps=[[float(v) for v in b]+[float(s)] for s,l,b in zip(d["scores"],d["labels"],d["boxes"])
            if int(l)==P.COCO_PERSON_LABEL and float(s)>=0.5]
        cnt.append(len(ps))
        if ps:
            a=np.array(ps); H,W=rgb.shape[:2]
            areas=(a[:,2]-a[:,0])*(a[:,3]-a[:,1])
            cx=(a[:,0]+a[:,2])/2; cy=(a[:,1]+a[:,3])/2
            if len(ps)>=2: agree.append(int(np.argmax(areas))==int(np.argmin(np.hypot(cx-W/2,cy-H/2))))
            cur=a[int(np.argmax(areas))][:4]
            if prev is not None:
                xa,ya=max(prev[0],cur[0]),max(prev[1],cur[1]); xb,yb=min(prev[2],cur[2]),min(prev[3],cur[3])
                it=max(0,xb-xa)*max(0,yb-ya)
                u=(prev[2]-prev[0])*(prev[3]-prev[1])+(cur[2]-cur[0])*(cur[3]-cur[1])-it
                ious.append(it/u if u>0 else 0)
            prev=cur
    print(f"{p.name:28s} {len(frames):3d}f  후보 med {np.median(cnt):.0f} max {max(cnt)}  "
          f"다인프레임 {np.mean([c>=2 for c in cnt]):.0%}  "
          f"최대=최중앙 {np.mean(agree):.0%}" if agree else
          f"{p.name:28s} {len(frames):3d}f  후보 med {np.median(cnt):.0f} max {max(cnt)}  "
          f"다인프레임 {np.mean([c>=2 for c in cnt]):.0%}  최대=최중앙 n/a(단일)", flush=True)
    print(f"{'':28s} 연속IoU med {np.median(ious):.2f}" if ious else "", flush=True)
