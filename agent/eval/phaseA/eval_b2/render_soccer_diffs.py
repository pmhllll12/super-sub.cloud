"""달라진 축구 프레임을 검수용으로 렌더 (후보 전부 동일 스타일)."""
import sys, csv
from pathlib import Path
import cv2, numpy as np, torch
sys.path.insert(0,"/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent.pose import PERSON_DETECTOR, COCO_PERSON_LABEL, DEFAULT_TARGET_FPS, read_frames
from transformers import AutoProcessor, RTDetrForObjectDetection
OUT=Path("/mnt/d/supersub-phaseA/eval_b2/review_cases"); OUT.mkdir(exist_ok=True)
rows=list(csv.DictReader(open("/mnt/d/supersub-phaseA/eval_b2/other_sports_diffs.csv")))
want={}
for r in rows: want.setdefault(r["video"],set()).add(int(r["frame"]))
dev="cuda" if torch.cuda.is_available() else "cpu"
p=AutoProcessor.from_pretrained(PERSON_DETECTOR)
d=RTDetrForObjectDetection.from_pretrained(PERSON_DETECTOR).to(dev).eval()
root=Path("/home/ho/projects/super-sub.cloud/agent/data/goldenset/soccerkicks_video")
for vid,fs in want.items():
    frames,_,_=read_frames(str(root/vid),target_fps=DEFAULT_TARGET_FPS)
    for t in sorted(fs):
        rgb=cv2.cvtColor(frames[t],cv2.COLOR_BGR2RGB)
        inp=p(images=rgb,return_tensors="pt").to(dev)
        with torch.inference_mode(): o=d(**inp)
        det=p.post_process_object_detection(o,target_sizes=[(rgb.shape[0],rgb.shape[1])],threshold=0.3)[0]
        boxes=[[float(v) for v in b]+[float(s)] for s,l,b in zip(det["scores"],det["labels"],det["boxes"])
               if int(l)==COCO_PERSON_LABEL and float(s)>=0.5]
        img=frames[t].copy(); h0,w0=img.shape[:2]
        tw=1100; img=cv2.resize(img,(tw,int(h0*tw/w0)),interpolation=cv2.INTER_CUBIC if w0<tw else cv2.INTER_AREA)
        s=img.shape[1]/w0
        for i,(x1,y1,x2,y2,sc) in enumerate(boxes):
            cv2.rectangle(img,(int(x1*s),int(y1*s)),(int(x2*s),int(y2*s)),(255,200,0),2,cv2.LINE_AA)
            lab=f"{i}  {sc:.2f}"
            (a,b2),_=cv2.getTextSize(lab,cv2.FONT_HERSHEY_SIMPLEX,0.5,1)
            ty=int(y1*s)-4 if int(y1*s)-b2-8>=0 else int(y1*s)+b2+6
            cv2.rectangle(img,(int(x1*s),ty-b2-4),(int(x1*s)+a+8,ty+4),(0,0,0),-1)
            cv2.putText(img,lab,(int(x1*s)+4,ty),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1,cv2.LINE_AA)
        hdr=np.zeros((30,img.shape[1],3),np.uint8)
        cv2.putText(hdr,f"{vid}  frame {t}  candidates {len(boxes)}",(8,21),
                    cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),1,cv2.LINE_AA)
        cv2.imwrite(str(OUT/f"SOCCER_{vid.replace('.avi','')}@f{t:03d}.jpg"),
                    np.vstack([hdr,img]),[cv2.IMWRITE_JPEG_QUALITY,88])
        print("wrote",vid,t,flush=True)
