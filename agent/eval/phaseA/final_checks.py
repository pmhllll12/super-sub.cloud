import sys, csv, json
from pathlib import Path
import numpy as np
sys.path.insert(0,"/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import features as F
ROOT=Path("/mnt/d/supersub-phaseA")
feats=json.loads((ROOT/"phaseA_features.json").read_text())
pose={r["clip_id"]:r for r in csv.DictReader(open(ROOT/"phaseA_pose.csv"))}
N=len(pose)

print("=== 9) swing_side ===")
from collections import Counter
print("  auto가 고른 팔:", Counter(r["auto_arm_side"] for r in pose.values()).most_common())
gl=sum(1 for r in pose.values() if r["gate_arm_left"] not in("","None"))
gr=sum(1 for r in pose.values() if r["gate_arm_right"] not in("","None"))
ga=sum(1 for r in pose.values() if r["gate_arm"] not in("","None"))
print(f"  게이트: auto {ga}/{N}  left지정 {gl}/{N}  right지정 {gr}/{N}")
# 좌/우 지정이 같은 클립에서 지표를 얼마나 바꾸는가
both=[c for c in feats.values() if c["arm_ext_left"]["ok"] and c["arm_ext_right"]["ok"]]
print(f"  좌·우 둘 다 산출된 클립 {len(both)}건에서 지정에 따른 차이:")
for m in ["swing_elbow_angle_at_impact","impact_frame","hip_shoulder_separation_deg"]:
    d=[abs(c["arm_ext_left"][m]-c["arm_ext_right"][m]) for c in both
       if m in c["arm_ext_left"] and m in c["arm_ext_right"]]
    if d: print(f"    {m:38s} |차이| med {np.median(d):.1f}  max {max(d):.1f}  (n={len(d)})")

print("\n=== 8) 이상치 / 경계값 ===")
CFG="arm_ext_right"
ok=[c[CFG] for c in feats.values() if c[CFG]["ok"]]
for m,(lo,hi) in F.PLAUSIBLE_RANGE.items():
    v=[c[m] for c in ok if m in c]
    if not v: continue
    # 각도 지표에서 생리학적으로 의심스러운 극단
    if m.endswith("knee_angle_at_impact"):
        bad=[x for x in v if x<90]
        print(f"  {m:42s} 90도 미만(과굴곡·측정붕괴 의심) {len(bad)}/{len(v)} ({len(bad)/len(v):.0%})")
    if m=="hip_rotation_range_deg":
        bad=[x for x in v if x>90]
        print(f"  {m:42s} 90도 초과(축 뒤집힘 의심)      {len(bad)}/{len(v)} ({len(bad)/len(v):.0%})")
    if m=="hip_shoulder_separation_deg":
        bad=[x for x in v if x<15]
        print(f"  {m:42s} 15도 미만(투구루브릭 0등급대)   {len(bad)}/{len(v)} ({len(bad)/len(v):.0%})")

print("\n=== 12) GO 기준 대조 ===")
gate_any=sum(1 for r in pose.values() if r["gate_arm_left"] not in("","None") or r["gate_arm_right"] not in("","None"))
print(f"  pose gate 통과율 >= 30%          : {gate_any}/{N} = {gate_any/N:.0%}  -> {'충족' if gate_any/N>=0.30 else '미달'}")
core=[c["arm_ext_right"] for c in feats.values() if c["arm_ext_right"]["ok"]]
hs=sum(1 for c in core if "hip_shoulder_separation_deg" in c)
hr=sum(1 for c in core if "hip_rotation_range_deg" in c)
print(f"  hip/shoulder 지표 산출률 >= 80%  : {hs}/{len(core)}={hs/len(core):.0%}, {hr}/{len(core)}={hr/len(core):.0%} -> {'충족' if min(hs,hr)/len(core)>=0.8 else '미달'}")
inb=sum(1 for r in pose.values() if r["rp_peak_pos"] not in("","None") and 0.2<=float(r["rp_peak_pos"])<=0.8)
print(f"  rotation peak 20~80% >= 70%      : {inb}/{N} = {inb/N:.0%}  -> {'충족' if inb/N>=0.70 else '미달'}")
print(f"  육안 20건 중 >= 15건 일치        : hit 6 + near 2 = 8/20 = 40%  -> 미달")
multi=sum(1 for r in pose.values() if int(r["rp_n_peaks"])>1)
print(f"  (참고) 다중 peak                 : {multi}/{N} = {multi/N:.0%}")
