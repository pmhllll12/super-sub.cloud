"""Phase B-2 집계 — 5개 selector 비교, 전이, continuity 고착, centrality 실패 분석."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
OUT = ROOT / "eval_b2"
MODES = ["baseline", "A", "B", "A_pose", "B_pose"]
LABEL = {"baseline": "Baseline", "A": "A-geometry", "B": "B-geometry",
         "A_pose": "A-pose", "B_pose": "B-pose"}
KNOWN = {"3R1kvNrGJK0", "O2GSaYqH8JY", "gg5xRWjw3f8", "xMIUw5mi3Eo"}

frames = list(csv.DictReader(open(OUT / "selector_eval_frames.csv")))
clips = list(csv.DictReader(open(OUT / "selector_eval_clips.csv")))
cent = list(csv.DictReader(open(OUT / "centrality_analysis.csv")))
cfg = json.loads((OUT / "pose_quality_config.json").read_text())

by = defaultdict(dict)
for r in frames:
    by[(r["clip_id"], r["ratio"])][r["selector"]] = r
mode_rows = defaultdict(list)
for r in frames:
    mode_rows[r["selector"]].append(r)


def stats(rows, sub=None):
    v = [r for r in rows if r["correct"] != ""]
    if sub:
        v = [r for r in v if sub(r)]
    n = len(v); c = sum(int(r["correct"]) for r in v)
    return n, c, n - c, (0 if not n else (n - c) / n), (0 if not n else c / n)


print("## 3. Pose quality")
print(f"  정의: {cfg['pose_quality']}")
print(f"  valid_joint_count: {cfg['valid_joint_count']}  (관측용, production 임계값 아님)")
print(f"  model: {cfg['model']}  det_threshold: {cfg['det_threshold']}  max_batch: {cfg['max_batch']}")
print(f"  총 후보: {cfg['total_candidates']}   총 시간 {cfg['total_seconds']/60:.1f}분")
print(f"  clip당 mean {cfg['clip_mean_seconds']:.1f}s  median {cfg['clip_median_seconds']:.1f}s")
print(f"  OOM 발생: {cfg['oom_events']}회")
tim = list(csv.DictReader(open(OUT / "pose_quality_timing.csv")))
buckets = defaultdict(list)
for t in tim:
    n = int(t["candidates"]); f = int(t["frames"])
    buckets[("~2/frame" if n / f < 2 else ("2-4/frame" if n / f < 4 else "4+/frame"))].append(
        float(t["ms_per_candidate"]))
for k in ("~2/frame", "2-4/frame", "4+/frame"):
    if buckets[k]:
        print(f"  후보밀도 {k:10s} clip {len(buckets[k]):2d}개  {np.mean(buckets[k]):.0f} ms/cand")

print("\n## 4. Main result")
res = {m: {"all": stats(mode_rows[m]),
           "multi": stats(mode_rows[m], lambda r: int(r["num_candidates"]) >= 2)}
       for m in MODES}
cl = defaultdict(dict)
for r in clips:
    cl[r["selector"]][r["clip_id"]] = r
cliprow, sw = {}, {}
for m in MODES:
    ev = [r for r in cl[m].values() if r["clip_correct"] != ""]
    ok = sum(int(r["clip_correct"]) for r in ev)
    cliprow[m] = (len(ev), ok, ok / len(ev))
    vals = [float(r["switch_rate"]) for r in cl[m].values() if r["switch_rate"] != ""]
    sw[m] = (float(np.median(vals)), float(np.mean(vals)), sum(1 for v in vals if v > 0.10), len(vals))

hdr = " | ".join(LABEL[m] for m in MODES)
print(f"| Metric | {hdr} |")
print("|---|" + "---:|" * len(MODES))
def row(name, fn):
    print(f"| {name} | " + " | ".join(fn(m) for m in MODES) + " |")
row("Correct", lambda m: str(res[m]["all"][1]))
row("Wrong", lambda m: str(res[m]["all"][2]))
row("Wrong-person rate", lambda m: f"{res[m]['all'][3]:.1%}")
row("Accuracy", lambda m: f"{res[m]['all'][4]:.1%}")
row("Multi-cand correct", lambda m: f"{res[m]['multi'][1]}/{res[m]['multi'][0]}")
row("Multi-cand wrong-rate", lambda m: f"{res[m]['multi'][3]:.1%}")
row("Multi-cand accuracy", lambda m: f"{res[m]['multi'][4]:.1%}")
row("Clip-level accuracy", lambda m: f"{cliprow[m][2]:.1%} ({cliprow[m][1]}/{cliprow[m][0]})")
row("Switching median", lambda m: f"{sw[m][0]:.1%}")
row("Switching mean", lambda m: f"{sw[m][1]:.1%}")
row("Clips >10% switching", lambda m: f"{sw[m][2]}/{sw[m][3]}")

print("\n## 5. Error transition")
idx = {m: {k: v[m] for k, v in by.items()} for m in MODES}
pairs = [("baseline", "A"), ("baseline", "B"), ("baseline", "A_pose"), ("baseline", "B_pose"),
         ("A", "A_pose"), ("B", "B_pose"), ("A_pose", "B_pose"), ("A", "B")]
trans_detail = []
for src, dst in pairs:
    rec, reg = [], []
    for k in idx[src]:
        if idx[src][k]["correct"] == "":
            continue
        cs, cd = int(idx[src][k]["correct"]), int(idx[dst][k]["correct"])
        if not cs and cd: rec.append(k)
        if cs and not cd: reg.append(k)
    print(f"  {LABEL[src]:12s} -> {LABEL[dst]:12s}  recovery {len(rec):2d}   regression {len(reg):2d}"
          f"   net {len(rec)-len(reg):+d}")
    for k in reg:
        r = idx[dst][k]
        trans_detail.append({"transition": f"{src}->{dst}", "type": "regression",
                             "clip_id": k[0], "ratio": k[1], "frame": r["frame"],
                             "gt_box_index": idx[src][k]["gt_box_index"],
                             "src_box": idx[src][k]["selected_box_index"],
                             "dst_box": r["selected_box_index"],
                             "num_candidates": r["num_candidates"],
                             "num_candidates_ge50": r["num_candidates_ge50"],
                             "dst_centrality": r["centrality"], "dst_size": r["size"],
                             "dst_pose_quality": r["pose_quality"], "dst_continuity": r["continuity"]})
    for k in rec:
        r = idx[dst][k]
        trans_detail.append({"transition": f"{src}->{dst}", "type": "recovery",
                             "clip_id": k[0], "ratio": k[1], "frame": r["frame"],
                             "gt_box_index": idx[src][k]["gt_box_index"],
                             "src_box": idx[src][k]["selected_box_index"],
                             "dst_box": r["selected_box_index"],
                             "num_candidates": r["num_candidates"],
                             "num_candidates_ge50": r["num_candidates_ge50"],
                             "dst_centrality": r["centrality"], "dst_size": r["size"],
                             "dst_pose_quality": r["pose_quality"], "dst_continuity": r["continuity"]})
with open(OUT / "selector_eval_transitions.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(trans_detail[0])); w.writeheader(); w.writerows(trans_detail)
reg_only = [d for d in trans_detail if d["type"] == "regression"]
with open(OUT / "regression_cases.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(reg_only[0])); w.writeheader(); w.writerows(reg_only)

print("\n## 6. Continuity 고착 분석 (continuity 구간별)")
BINS = [(0.0, 0.3, "<0.3"), (0.3, 0.6, "0.3-0.6"), (0.6, 0.8, "0.6-0.8"), (0.8, 1.01, ">=0.8")]
for m in ("B", "B_pose"):
    print(f"  [{LABEL[m]}]")
    v = [r for r in mode_rows[m] if r["correct"] != ""]
    for lo, hi, name in BINS:
        s = [r for r in v if lo <= float(r["continuity"]) < hi]
        if not s:
            print(f"    {name:8s}  n=0"); continue
        c = sum(int(r["correct"]) for r in s)
        # 이 구간에서 A(같은 계열, continuity 없는 쪽) 대비 회귀한 수
        base_mode = "A" if m == "B" else "A_pose"
        regs = sum(1 for r in s
                   if int(idx[base_mode][(r["clip_id"], r["ratio"])]["correct"]) == 1
                   and int(r["correct"]) == 0)
        print(f"    {name:8s}  n={len(s):3d}  correct {c:3d}  wrong {len(s)-c:3d}"
              f"  ({(len(s)-c)/len(s):5.1%} wrong)   {base_mode} 대비 regression {regs}")

print("\n## 7. Centrality failure analysis")
gc = [float(r["gt_centrality"]) for r in cent if r["gt_centrality"] != ""]
print(f"  GT centrality 분포 (n={len(gc)}): p10 {np.percentile(gc,10):.2f} "
      f"median {np.median(gc):.2f} p90 {np.percentile(gc,90):.2f}  min {min(gc):.2f}")
rank = Counter(int(r["centrality_rank"]) for r in cent if r["centrality_rank"] != "")
print(f"  GT가 중앙성 1위인 대상: {rank[1]}/{sum(rank.values())} ({rank[1]/sum(rank.values()):.0%})")
print(f"  GT 중앙성 순위 분포: {dict(sorted(rank.items())[:6])}")
multi_c = [r for r in cent if int(r["n_candidates_ge50"]) >= 2 and r["centrality_rank"] != ""]
notop = [r for r in multi_c if int(r["centrality_rank"]) > 1]
print(f"  후보 2개 이상 중 GT가 중앙성 1위가 아닌 대상: {len(notop)}/{len(multi_c)}")
print(f"  {'clip@ratio':24s} {'cand':>4s} {'GT cen':>7s} {'max cen':>7s} {'rank':>4s}  base/A/B/Ap/Bp")
for r in sorted(notop, key=lambda x: float(x["gt_centrality"]))[:14]:
    k = (r["clip_id"], r["ratio"])
    cc = "".join("-" if idx[m][k]["correct"] == "" else ("O" if int(idx[m][k]["correct"]) else "X")
                 for m in MODES)
    print(f"  {r['clip_id']+'@'+r['ratio']:24s} {r['n_candidates_ge50']:>4s} "
          f"{r['gt_centrality']:>7s} {r['max_centrality']:>7s} {r['centrality_rank']:>4s}  {cc}")
# 중앙성 낮은 GT에서 baseline이 더 나은가
low = [r for r in multi_c if float(r["gt_centrality"]) < np.median(gc)]
high = [r for r in multi_c if float(r["gt_centrality"]) >= np.median(gc)]
for name, grp in (("GT centrality < median", low), ("GT centrality >= median", high)):
    if not grp: continue
    print(f"  [{name}] n={len(grp)}")
    for m in MODES:
        c = sum(1 for r in grp if int(idx[m][(r["clip_id"], r["ratio"])]["correct"]) == 1)
        print(f"      {LABEL[m]:12s} {c}/{len(grp)} = {c/len(grp):.1%}")

print("\n## 독립성 민감도 (known 4클립 제외)")
for m in MODES:
    a = stats(mode_rows[m]); e = stats(mode_rows[m], lambda r: r["clip_id"] not in KNOWN)
    am = stats(mode_rows[m], lambda r: int(r["num_candidates"]) >= 2)
    em = stats(mode_rows[m], lambda r: int(r["num_candidates"]) >= 2 and r["clip_id"] not in KNOWN)
    print(f"  {LABEL[m]:12s} 전체 {a[1]}/{a[0]}={a[4]:.1%}  제외 {e[1]}/{e[0]}={e[4]:.1%}"
          f"   multi {am[1]}/{am[0]}={am[4]:.1%}  제외 {em[1]}/{em[0]}={em[4]:.1%}")

print("\n## Known clips")
for cid in sorted(KNOWN):
    for ratio in ("0.20", "0.50", "0.80"):
        k = (cid, ratio); r0 = idx["baseline"][k]
        g = r0["gt_box_index"] or "null"
        picks = "/".join(idx[m][k]["selected_box_index"] or "-" for m in MODES)
        cc = "".join("-" if idx[m][k]["correct"] == "" else ("O" if int(idx[m][k]["correct"]) else "X")
                     for m in MODES)
        print(f"  {cid:14s} {ratio} cand={r0['num_candidates']:>2s} GT={g:>4s} picks={picks:12s} {cc}")
