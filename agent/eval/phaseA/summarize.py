"""Phase A 요약 — 게이트 통과율, 지표 분포, rotation peak 평가."""
import json, csv, statistics as st
from pathlib import Path
import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
rows = list(csv.DictReader(open(ROOT/"phaseA_pose.csv")))
feats = json.loads((ROOT/"phaseA_features.json").read_text())
specs = {r["clip_id"]: r for r in csv.DictReader(open(ROOT/"clip_specs.csv"))}
N = len(rows)

def f(v):
    return None if v in ("", "None", None) else float(v)

def pct(n): return f"{n}/{N} ({n/N:.0%})"

print(f"=== 클립 {N}건 ===\n")

print("## 1. 포즈 게이트")
for k, lab in [("gate_arm","arm auto"),("gate_arm_left","arm left"),("gate_arm_right","arm right"),
               ("gate_leg","leg auto"),("gate_leg_left","leg left"),("gate_leg_right","leg right")]:
    ok = [r for r in rows if f(r[k]) is not None]
    vals = [f(r[k]) for r in ok]
    print(f"  {lab:10s} 통과 {pct(len(ok)):14s}"
          + (f" 유효프레임 median {st.median(vals):.0%}" if vals else ""))
# arm은 left/right 중 하나라도 통과하면 지정으로 살릴 수 있다
either = sum(1 for r in rows if f(r["gate_arm_left"]) is not None or f(r["gate_arm_right"]) is not None)
print(f"  arm left|right 중 하나라도 통과: {pct(either)}")

print("\n## 2. 키포인트 품질 (신뢰도 0.3 이상 양측 프레임 비율의 중앙값)")
for j in ["shoulder","elbow","wrist","hip","knee","ankle"]:
    v = [f(r[f"q_{j}_ok"]) for r in rows]
    m = [f(r[f"q_{j}_mean"]) for r in rows]
    print(f"  {j:9s} ok median {st.median(v):.0%}   mean conf median {st.median(m):.2f}")
print(f"  valid_arm(0.6) median {st.median([f(r['valid_arm_ratio']) for r in rows]):.0%}"
      f"   valid_leg(0.3) median {st.median([f(r['valid_leg_ratio']) for r in rows]):.0%}")

print("\n## 3. 지표 산출률 / 분포")
CFG = ["arm_ext_auto","arm_ext_left","arm_ext_right","leg_ext_auto","arm_apex_auto"]
for cfg in CFG:
    ok = [c[cfg] for c in feats.values() if c[cfg]["ok"]]
    print(f"\n  [{cfg}] extract_features 성공 {len(ok)}/{N} ({len(ok)/N:.0%})")
    if not ok: 
        from collections import Counter
        print("   ", Counter(c[cfg]["err"].split(":")[0] for c in feats.values()).most_common())
        continue
    for m in ["hip_shoulder_separation_deg","hip_rotation_range_deg",
              "trunk_forward_lean_deg_at_impact","plant_knee_angle_at_impact",
              "swing_knee_angle_at_impact","swing_elbow_angle_at_impact",
              "support_elbow_angle_at_impact","swing_shoulder_flexion_after_impact_deg"]:
        v = sorted(c[m] for c in ok if m in c)
        if not v:
            print(f"    {m:42s} 0/{len(ok)}"); continue
        q = lambda p: v[min(len(v)-1, int(round(p*(len(v)-1))))]
        print(f"    {m:42s} {len(v)}/{len(ok)} ({len(v)/len(ok):.0%})  "
              f"p10 {q(.1):6.1f}  med {q(.5):6.1f}  p90 {q(.9):6.1f}  "
              f"[{v[0]:.1f}, {v[-1]:.1f}]")

print("\n## 4. rotation peak 후보")
have = [r for r in rows if f(r["rp_peak_frame"]) is not None]
print(f"  산출 성공 {pct(len(have))}")
pos = [f(r["rp_peak_pos"]) for r in have]
inband = [p for p in pos if 0.2 <= p <= 0.8]
print(f"  20~80% 구간: {len(inband)}/{len(have)} ({len(inband)/len(have):.0%})")
print(f"  위치 분포: p10 {np.percentile(pos,10):.2f} med {np.median(pos):.2f} p90 {np.percentile(pos,90):.2f}")
npk = [int(r["rp_n_peaks"]) for r in have]
from collections import Counter
print(f"  peak 개수: {sorted(Counter(npk).items())}  (다중 peak {sum(1 for n in npk if n>1)}/{len(have)})")
ax = [f(r["rp_axis_ok_ratio"]) for r in rows]
print(f"  어깨축 가용 프레임 비율: med {st.median(ax):.0%}  (<30%인 클립 {sum(1 for a in ax if a<0.3)}건)")

print("\n## 5. 도구 검출")
for name in ["baseball_bat","sports_ball","tennis_racket"]:
    surv = [r for r in rows if f(r[f"obj_{name}"]) is not None]
    print(f"  {name:14s} production 필터 통과 {pct(len(surv))}", end="")
    if surv:
        v = [f(r[f'obj_{name}']) for r in surv]
        print(f"  검출률 med {st.median(v):.0%}  0.8이상 프레임 med "
              f"{st.median([float(r[f'obj_{name}_hi']) for r in surv]):.0f}")
    else: print()
both = sum(1 for r in rows if f(r["obj_baseball_bat"]) is not None and f(r["obj_tennis_racket"]) is not None)
print(f"  bat·racket 동시 검출(오검출 의심): {both}건")

print("\n## 6. 해상도 × 게이트")
for lo, hi, lab in [(0,300,"~300px"),(300,600,"300-600px"),(600,1000,"600-1000px"),(1000,9999,"1000px+")]:
    sub = [r for r in rows if lo <= int(specs[r["clip_id"]]["h"]) < hi]
    if not sub: continue
    g = sum(1 for r in sub if f(r["gate_arm_left"]) is not None or f(r["gate_arm_right"]) is not None)
    print(f"  세로 {lab:11s} {len(sub):2d}건  arm게이트(측 지정) {g}/{len(sub)}")
