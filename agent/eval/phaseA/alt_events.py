"""대체 임팩트 이벤트 후보 비교 + 피사체 안정성 정량화 (READ-ONLY)."""
import sys, csv, json
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import features as F

ROOT = Path("/mnt/d/supersub-phaseA"); CACHE = ROOT/"cache"
specs = {r["clip_id"]: r for r in csv.DictReader(open(ROOT/"clip_specs.csv"))}

def peaks_of(vel, ok, frac=0.6, sep=3):
    v = np.where(ok & np.isfinite(vel), vel, -np.inf)
    if not np.isfinite(v).any(): return None, 0
    top = int(np.argmax(v)); thr = v[top]*frac
    cand=[i for i in range(1,len(v)-1) if v[i]>=thr and v[i]>=v[i-1] and v[i]>=v[i+1]]
    merged=[]
    for c in cand:
        if not merged or c-merged[-1]>sep: merged.append(c)
    return top, len(merged)

rows=[]
for p in sorted(CACHE.glob("*.npz")):
    cid=p.stem; d=np.load(p)
    kps=d["keypoints"]; T=len(kps)
    objs={k[4:]:d[k] for k in d.files if k.startswith("obj_")}
    sp=specs[cid]; fh=int(sp["h"])
    r={"clip_id":cid,"T":T}

    # 피사체 크기 = 어깨~발목 세로 폭 / 프레임 높이 (검출된 프레임의 중앙값)
    det=kps[:,:,2].max(axis=1)>0
    if det.sum():
        ys=kps[det][:,:, 1]; cs=kps[det][:,:,2]
        span=[np.ptp(y[c>=0.3]) for y,c in zip(ys,cs) if (c>=0.3).sum()>=4]
        r["subject_scale"]=round(float(np.median(span))/fh,3) if span else None
    # 피사체 스위칭 대용: 골반 중심 이동량 / 어깨너비, 상위 이상치 비율
    xy=kps[:,:,:2]; hip=(xy[:,F.L_HIP]+xy[:,F.R_HIP])/2
    sw=np.linalg.norm(xy[:,F.L_SHOULDER]-xy[:,F.R_SHOULDER],axis=1)
    good=(kps[:,[F.L_HIP,F.R_HIP,F.L_SHOULDER,F.R_SHOULDER],2]>=0.3).all(axis=1)&(sw>1e-6)
    jump=np.full(T-1,np.nan)
    for t in range(T-1):
        if good[t] and good[t+1]:
            jump[t]=np.linalg.norm(hip[t+1]-hip[t])/max(sw[t],1e-6)
    fin=jump[np.isfinite(jump)]
    r["jump_med"]=round(float(np.median(fin)),3) if fin.size else None
    # 어깨너비의 1.5배 이상 순간이동 = 다른 사람으로 갈아탄 정황
    r["switch_frac"]=round(float((fin>1.5).mean()),3) if fin.size else None
    r["det_ratio"]=round(float(det.mean()),3)

    norm=F.normalize(kps); nxy=norm[:,:,:2]
    # (a) rotation_peak (어깨축)
    okS=((norm[:,[F.L_SHOULDER,F.R_SHOULDER],2]>=F.MIN_CONFIDENCE).all(axis=1)
         &(np.linalg.norm(nxy[:,F.L_SHOULDER]-nxy[:,F.R_SHOULDER],axis=1)>=F.MIN_AXIS_LENGTH))
    sh=F._axis_deg(nxy[:,F.L_SHOULDER]-nxy[:,F.R_SHOULDER])
    vel=np.full(T,np.nan)
    if okS.sum()>=4:
        idx=np.where(okS)[0]; vel[idx]=np.abs(np.gradient(np.unwrap(sh[idx],period=180.0)))
    r["rot_peak"],r["rot_npk"]=peaks_of(vel,okS)

    # (b) wrist_speed_peak — 양 손목 중심의 속도 최대 (배트 스피드 대용)
    wc=(nxy[:,F.L_WRIST]+nxy[:,F.R_WRIST])/2
    okW=(norm[:,[F.L_WRIST,F.R_WRIST],2]>=0.3).all(axis=1)
    ws=np.full(T,np.nan); ws[1:]=np.linalg.norm(np.diff(wc,axis=0),axis=1)
    r["wrist_peak"],r["wrist_npk"]=peaks_of(ws,okW)
    r["wrist_ok"]=round(float(okW.mean()),3)

    # (c) bat_speed_peak — baseball_bat 궤적 속도 최대
    bat=objs.get("baseball_bat")
    if bat is not None:
        bt=F.normalize_track(bat,kps); okB=bat[:,2]>0
        bs=np.full(T,np.nan)
        for t in range(1,T):
            if okB[t] and okB[t-1]: bs[t]=np.linalg.norm(bt[t,:2]-bt[t-1,:2])
        r["bat_peak"],r["bat_npk"]=peaks_of(bs,okB&np.isfinite(bs))
        r["bat_ratio"]=round(float(okB.mean()),3)
    else:
        r["bat_peak"]=None; r["bat_npk"]=0; r["bat_ratio"]=None
    rows.append(r)

with open(ROOT/"alt_events.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

N=len(rows)
def stat(pre):
    have=[r for r in rows if r[f"{pre}_peak"] is not None]
    npk=[r[f"{pre}_npk"] for r in have]
    single=sum(1 for n in npk if n==1)
    pos=[r[f"{pre}_peak"]/(r["T"]-1) for r in have]
    inband=sum(1 for p in pos if 0.2<=p<=0.8)
    print(f"  {pre:6s} 산출 {len(have):2d}/{N} ({len(have)/N:.0%})  "
          f"단일peak {single}/{len(have)} ({single/max(1,len(have)):.0%})  "
          f"20-80% {inband}/{len(have)} ({inband/max(1,len(have)):.0%})  "
          f"peak중앙값개수 {int(np.median(npk)) if npk else 0}")
print("=== 이벤트 후보 비교 ===")
for pre in ("rot","wrist","bat"): stat(pre)

print("\n=== 피사체 안정성 ===")
sc=[r["subject_scale"] for r in rows if r["subject_scale"]]
print(f"  피사체 세로크기/프레임: p10 {np.percentile(sc,10):.2f} med {np.median(sc):.2f} p90 {np.percentile(sc,90):.2f}")
print(f"  0.3 미만(작음) {sum(1 for s in sc if s<0.3)}/{N}   0.5 이상(큼) {sum(1 for s in sc if s>=0.5)}/{N}")
sw=[r["switch_frac"] for r in rows if r["switch_frac"] is not None]
print(f"  피사체 스위칭 의심 프레임 비율: med {np.median(sw):.1%}  5%초과 클립 {sum(1 for s in sw if s>0.05)}/{N}")
