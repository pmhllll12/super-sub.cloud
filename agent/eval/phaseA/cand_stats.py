"""사람 후보 통계 — baseline selector의 실패 구조를 정량화한다 (READ-ONLY)."""
import sys, json, csv
from pathlib import Path
import numpy as np
sys.path.insert(0,"/home/ho/projects/super-sub.cloud/agent/src")
ROOT=Path("/mnt/d/supersub-phaseA"); C=ROOT/"candidates"

def unpack(f):
    d=np.load(f); n=d["n"]; b=d["boxes"]; out=[]; i=0
    for k in n: out.append(b[i:i+k]); i+=k
    return out, tuple(d["frame_wh"]), float(d["sampled_fps"])

def largest(ps, thr=0.5):
    """production _largest_person_box와 같은 규칙."""
    best,ba=None,0.0
    for x1,y1,x2,y2,s in ps:
        if s<thr: continue
        a=(x2-x1)*(y2-y1)
        if a>ba: best,ba=(x1,y1,x2,y2),a
    return best

def iou(a,b):
    if a is None or b is None: return 0.0
    xa=max(a[0],b[0]); ya=max(a[1],b[1]); xb=min(a[2],b[2]); yb=min(a[3],b[3])
    inter=max(0,xb-xa)*max(0,yb-ya)
    ua=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/ua if ua>0 else 0.0

rows=[]
for f in sorted(C.glob("*.npz")):
    cid=f.stem; per,(W,H),sfps=unpack(f)
    cnt=[int((p[:,4]>=0.5).sum()) for p in per]
    sel=[largest(p) for p in per]
    # 연속 프레임 선택 박스의 IoU — 낮으면 다른 사람으로 갈아탄 것
    ious=[iou(sel[t],sel[t+1]) for t in range(len(sel)-1)
          if sel[t] is not None and sel[t+1] is not None]
    # 최대 박스가 가장 중앙에 있는 후보와 같은가
    agree=[]
    for p in per:
        ok=p[p[:,4]>=0.5]
        if len(ok)<2: continue
        areas=(ok[:,2]-ok[:,0])*(ok[:,3]-ok[:,1])
        cx=(ok[:,0]+ok[:,2])/2; cy=(ok[:,1]+ok[:,3])/2
        dist=np.hypot(cx-W/2, cy-H/2)
        agree.append(int(np.argmax(areas))==int(np.argmin(dist)))
    rows.append(dict(clip_id=cid, frames=len(per), W=W, H=H,
        cand_med=float(np.median(cnt)), cand_max=int(max(cnt)) if cnt else 0,
        multi_frac=round(float(np.mean([c>=2 for c in cnt])),3),
        iou_med=round(float(np.median(ious)),3) if ious else None,
        iou_lt03=round(float(np.mean([i<0.3 for i in ious])),3) if ious else None,
        big_is_central=round(float(np.mean(agree)),3) if agree else None,
        multi_frames=len(agree)))

with open(ROOT/"cand_stats.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

N=len(rows)
cm=[r["cand_med"] for r in rows]
print(f"=== 사람 후보 ({N}클립) ===")
print(f"  프레임당 후보(score>=0.5) 중앙값: med {np.median(cm):.1f}  max {max(r['cand_max'] for r in rows)}")
print(f"  후보 1명인 클립(중앙값 기준): {sum(1 for c in cm if c<=1)}/{N}")
print(f"  후보 2명 이상 프레임 비율: med {np.median([r['multi_frac'] for r in rows]):.0%}"
      f"  (50% 초과 클립 {sum(1 for r in rows if r['multi_frac']>0.5)}/{N})")
bc=[r["big_is_central"] for r in rows if r["big_is_central"] is not None]
print(f"\n=== 최대박스 vs 최중앙 후보 일치율 (다인 프레임에서) ===")
print(f"  med {np.median(bc):.0%}   50% 미만 클립 {sum(1 for b in bc if b<0.5)}/{len(bc)}")
iv=[r["iou_med"] for r in rows if r["iou_med"] is not None]
lt=[r["iou_lt03"] for r in rows if r["iou_lt03"] is not None]
print(f"\n=== baseline 선택 박스의 프레임간 연속성 ===")
print(f"  연속 IoU med: {np.median(iv):.2f}")
print(f"  IoU<0.3 프레임 비율: med {np.median(lt):.1%}  (10% 초과 클립 {sum(1 for x in lt if x>0.1)}/{N})")
