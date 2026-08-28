"""후보 박스 시각화 — 최대(빨강) vs 최중앙(초록) 비교."""
import sys
from pathlib import Path
import numpy as np, cv2
ROOT=Path("/mnt/d/supersub-phaseA")
def unpack(f):
    d=np.load(f); n=d["n"]; b=d["boxes"]; out=[]; i=0
    for k in n: out.append(b[i:i+k]); i+=k
    return out, tuple(int(v) for v in d["frame_wh"])
for cid, ts in [("3R1kvNrGJK0",[30,53,70]), ("O2GSaYqH8JY",[100,106,112]),
                ("gg5xRWjw3f8",[66,92]), ("xMIUw5mi3Eo",[128,132])]:
    per,(W,H)=unpack(ROOT/"candidates"/f"{cid}.npz")
    tiles=[]
    for t in ts:
        img=cv2.imread(str(ROOT/"frames"/cid/f"{t:03d}.jpg"))
        if img is None: continue
        sc=img.shape[1]/W
        ok=per[t][per[t][:,4]>=0.5]
        if len(ok):
            areas=(ok[:,2]-ok[:,0])*(ok[:,3]-ok[:,1])
            cx=(ok[:,0]+ok[:,2])/2; cy=(ok[:,1]+ok[:,3])/2
            dist=np.hypot(cx-W/2, cy-H/2)
            ib, ic = int(np.argmax(areas)), int(np.argmin(dist))
            for j,(x1,y1,x2,y2,s) in enumerate(ok):
                col=(200,200,200); th=1
                if j==ib: col,th=(0,0,255),3
                if j==ic: col,th=(0,220,0),2
                if j==ib==ic: col,th=(0,220,255),3
                cv2.rectangle(img,(int(x1*sc),int(y1*sc)),(int(x2*sc),int(y2*sc)),col,th)
        bar=np.zeros((22,img.shape[1],3),np.uint8)
        cv2.putText(bar,f"{cid} f{t} n={len(ok)}",(4,16),cv2.FONT_HERSHEY_SIMPLEX,0.45,(255,255,255),1)
        tiles.append(np.vstack([bar,img]))
    if tiles:
        h=max(t.shape[0] for t in tiles)
        row=np.hstack([np.vstack([t,np.zeros((h-t.shape[0],t.shape[1],3),np.uint8)]) for t in tiles])
        cv2.imwrite(str(ROOT/f"cand_{cid}.jpg"),row,[cv2.IMWRITE_JPEG_QUALITY,85])
        print("wrote", cid)
