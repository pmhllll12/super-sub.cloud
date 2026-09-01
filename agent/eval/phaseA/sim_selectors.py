"""후보 selector A/B 오프라인 시뮬레이션 — 캐시된 person 박스만 사용.

pose quality(ViTPose)는 여기서 계산하지 않는다. 기하 신호만으로
baseline 대비 연속성이 얼마나 개선되는지 상한을 본다.
"""
import csv
from pathlib import Path
import numpy as np
ROOT=Path("/mnt/d/supersub-phaseA"); C=ROOT/"candidates"

def unpack(f):
    d=np.load(f); n=d["n"]; b=d["boxes"]; out=[]; i=0
    for k in n: out.append(b[i:i+k]); i+=k
    return out,(int(d["frame_wh"][0]),int(d["frame_wh"][1]))

def iou(a,b):
    if a is None or b is None: return 0.0
    xa,ya=max(a[0],b[0]),max(a[1],b[1]); xb,yb=min(a[2],b[2]),min(a[3],b[3])
    it=max(0,xb-xa)*max(0,yb-ya)
    u=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-it
    return it/u if u>0 else 0.0

def feats(a,W,H):
    ar=(a[:,2]-a[:,0])*(a[:,3]-a[:,1])
    cx=(a[:,0]+a[:,2])/2; cy=(a[:,1]+a[:,3])/2
    # 중앙성: 화면 중심에서의 거리를 대각선으로 정규화 → 1이 중앙
    cen=1.0-np.hypot(cx-W/2,cy-H/2)/(0.5*np.hypot(W,H))
    siz=ar/ar.max() if ar.max()>0 else ar
    return cen,siz,ar

def run(per,W,H,mode):
    """mode: base | A(중앙성+크기보조) | B(A+시간연속성)"""
    sel=[]; prev=None
    for a5 in per:
        a=a5[a5[:,4]>=0.5]
        if len(a)==0: sel.append(None); continue
        if len(a)==1: sel.append(a[0,:4]); prev=a[0,:4]; continue
        cen,siz,ar=feats(a,W,H)
        if mode=="base": s=ar
        elif mode=="A":  s=0.7*cen+0.3*siz
        else:
            cont=np.array([iou(prev,b[:4]) for b in a]) if prev is not None else np.zeros(len(a))
            s=0.45*cen+0.20*siz+0.35*cont
        j=int(np.argmax(s)); sel.append(a[j,:4]); prev=a[j,:4]
    return sel

rows=[]
for f in sorted(C.glob("*.npz")):
    cid=f.stem; per,(W,H)=unpack(f)
    r={"clip_id":cid}
    ref=None
    for mode in ("base","A","B"):
        sel=run(per,W,H,mode)
        pairs=[(sel[t],sel[t+1]) for t in range(len(sel)-1) if sel[t] is not None and sel[t+1] is not None]
        iv=[iou(x,y) for x,y in pairs]
        r[f"{mode}_iou_med"]=round(float(np.median(iv)),3) if iv else None
        r[f"{mode}_switch"]=round(float(np.mean([i<0.3 for i in iv])),3) if iv else None
        if mode=="base": ref=sel
        else:
            diff=[t for t in range(len(sel)) if (sel[t] is None)!=(ref[t] is None)
                  or (sel[t] is not None and ref[t] is not None and iou(sel[t],ref[t])<0.5)]
            r[f"{mode}_changed_frac"]=round(len(diff)/len(sel),3)
    rows.append(r)

with open(ROOT/"sim_selectors.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

N=len(rows)
print(f"=== selector 시뮬레이션 ({N}클립, 기하 신호만) ===")
for m,lab in [("base","baseball(최대박스)"),("A","A 중앙성+크기"),("B","B A+시간연속성")]:
    iv=[r[f"{m}_iou_med"] for r in rows if r[f"{m}_iou_med"] is not None]
    sw=[r[f"{m}_switch"] for r in rows if r[f"{m}_switch"] is not None]
    print(f"  {lab:22s} 연속IoU med {np.median(iv):.2f}  "
          f"스위칭(IoU<0.3) med {np.median(sw):.1%}  "
          f"스위칭>10% 클립 {sum(1 for x in sw if x>0.1)}/{N}")
for m in ("A","B"):
    ch=[r[f"{m}_changed_frac"] for r in rows]
    print(f"  {m}가 baseline과 다른 선택을 한 프레임 비율: med {np.median(ch):.0%}  "
          f"전혀 안 바뀐 클립 {sum(1 for c in ch if c==0)}/{N}")
