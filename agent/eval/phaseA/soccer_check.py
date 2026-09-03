import sys, glob
from pathlib import Path
import numpy as np, cv2, torch
from transformers import AutoProcessor, RTDetrForObjectDetection
sys.path.insert(0,"/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import pose as P
dev="cuda" if torch.cuda.is_available() else "cpu"
proc=AutoProcessor.from_pretrained(P.PERSON_DETECTOR)
det=RTDetrForObjectDetection.from_pretrained(P.PERSON_DETECTOR).to(dev).eval()
ps_=sorted(Path("/home/ho/projects/super-sub.cloud/agent/data/goldenset/soccerkicks_video").glob("*.avi"))[:8]
tot=[]
for p in ps_:
    frames,src,sf=P.read_frames(str(p),target_fps=P.DEFAULT_TARGET_FPS)
    cnt=[];agree=[]
    for fr in frames:
        rgb=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)
        inp=proc(images=rgb,return_tensors="pt").to(dev)
        with torch.inference_mode(): o=det(**inp)
        d=proc.post_process_object_detection(o,target_sizes=[(rgb.shape[0],rgb.shape[1])],threshold=0.3)[0]
        a=np.array([[float(v) for v in b]+[float(s)] for s,l,b in zip(d["scores"],d["labels"],d["boxes"])
            if int(l)==P.COCO_PERSON_LABEL and float(s)>=0.5]) if len(d["scores"]) else np.zeros((0,5))
        cnt.append(len(a))
        if len(a)>=2:
            H,W=rgb.shape[:2]
            areas=(a[:,2]-a[:,0])*(a[:,3]-a[:,1]); cx=(a[:,0]+a[:,2])/2; cy=(a[:,1]+a[:,3])/2
            agree.append(int(np.argmax(areas))==int(np.argmin(np.hypot(cx-W/2,cy-H/2))))
    m=float(np.mean([c>=2 for c in cnt])); tot.append(m)
    print(f"{p.name:24s} {len(frames):3d}f 후보 med {np.median(cnt):.0f} max {max(cnt)} "
          f"다인 {m:.0%} 최대=최중앙 {(np.mean(agree) if agree else float('nan')):.0%}", flush=True)
print(f"\n축구 {len(ps_)}건 다인프레임 비율 med {np.median(tot):.0%}")
