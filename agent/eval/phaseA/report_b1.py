"""Phase B-1 집계 — 지표·전이표·민감도 분석. 계산만 하고 판단하지 않는다."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
OUT = ROOT / "eval_b1"
MODES = ["baseline", "A", "B"]
LABEL = {"baseline": "Baseline", "A": "A-geometry", "B": "B-geometry"}
KNOWN = {"3R1kvNrGJK0", "O2GSaYqH8JY", "gg5xRWjw3f8", "xMIUw5mi3Eo"}

frames = list(csv.DictReader(open(OUT / "selector_eval_frames.csv")))
clips = list(csv.DictReader(open(OUT / "selector_eval_clips.csv")))
labels = json.loads((ROOT / "labeling" / "labels.json").read_text())

by_mode = defaultdict(list)
for r in frames:
    by_mode[r["selector"]].append(r)


def key(r):
    return (r["clip_id"], r["ratio"])


def stats(rows, subset=None):
    v = [r for r in rows if r["correct"] != ""]
    if subset:
        v = [r for r in v if subset(r)]
    n = len(v)
    c = sum(int(r["correct"]) for r in v)
    return n, c, n - c, (0.0 if n == 0 else (n - c) / n), (0.0 if n == 0 else c / n)


print("=" * 74)
print("## 2. Ground Truth")
tot = len(labels["frames"])
nulls = [r for r in labels["frames"] if r["box_index"] is None]
print(f"  targets: {tot}")
print(f"  valid:   {tot - len(nulls)}")
print(f"  null:    {len(nulls)}  ({len(nulls)/tot:.0%})")
from collections import Counter
cr = Counter(r["ratio"] for r in nulls)
print(f"  null by ratio: 20% {cr[0.2]}/39  50% {cr[0.5]}/39  80% {cr[0.8]}/39")
nc = Counter(r["clip_id"] for r in nulls)
print(f"  null이 있는 clip: {len(nc)}개 / 3개 모두 null인 clip: "
      f"{sum(1 for c,n in nc.items() if n==3)}개 ({[c for c,n in nc.items() if n==3]})")
base = by_mode["baseline"]
multi = [r for r in base if r["correct"] != "" and int(r["num_candidates"]) >= 2]
multi50 = [r for r in base if r["correct"] != "" and int(r["num_candidates_ge50"]) >= 2]
print(f"  multi-candidate valid (>=0.3 기준): {len(multi)}")
print(f"  multi-candidate valid (>=0.5, selector가 실제로 보는 집합): {len(multi50)}")

# 도달 불가 GT — GT가 score<0.5 후보를 가리켜 어떤 selector도 못 맞히는 대상
unreachable = [r for r in base if r["correct"] != "" and float(r["det_score"]) >= 0
               and int(r["num_candidates_ge50"]) > 0
               and r["gt_box_index"] != "" ]
# 정확히 판정하려면 GT 박스 점수가 필요 — frames CSV엔 selector 쪽 점수만 있으므로 재확인
import sys
sys.path.insert(0, "/mnt/d/supersub-phaseA/labeling")
from targets import load_candidates  # noqa: E402
cache = {}
unreach = []
for r in base:
    if r["correct"] == "":
        continue
    cid = r["clip_id"]
    if cid not in cache:
        cache[cid], _, _ = load_candidates(cid)
    b = cache[cid][int(r["frame"])]
    if b[int(r["gt_box_index"]), 4] < 0.5:
        unreach.append((cid, r["ratio"], round(float(b[int(r["gt_box_index"]), 4]), 2)))
print(f"  도달 불가 GT (GT 후보 score<0.5): {len(unreach)}  {unreach}")

print()
print("## 3. Main Result")
print(f"| Metric | {' | '.join(LABEL[m] for m in MODES)} |")
print("|---|---:|---:|---:|")
rows = {}
for m in MODES:
    rows[m] = {
        "all": stats(by_mode[m]),
        "multi": stats(by_mode[m], lambda r: int(r["num_candidates"]) >= 2),
        "multi50": stats(by_mode[m], lambda r: int(r["num_candidates_ge50"]) >= 2),
    }
print(f"| Valid GT | {' | '.join(str(rows[m]['all'][0]) for m in MODES)} |")
print(f"| Correct | {' | '.join(str(rows[m]['all'][1]) for m in MODES)} |")
print(f"| Wrong | {' | '.join(str(rows[m]['all'][2]) for m in MODES)} |")
print(f"| Wrong-person rate | {' | '.join(f'{rows[m]['all'][3]:.1%}' for m in MODES)} |")
print(f"| Accuracy | {' | '.join(f'{rows[m]['all'][4]:.1%}' for m in MODES)} |")
print(f"| Multi-cand valid GT | {' | '.join(str(rows[m]['multi'][0]) for m in MODES)} |")
print(f"| Multi-cand wrong-person rate | {' | '.join(f'{rows[m]['multi'][3]:.1%}' for m in MODES)} |")
print(f"| Multi-cand accuracy | {' | '.join(f'{rows[m]['multi'][4]:.1%}' for m in MODES)} |")

# clip-level
cl = defaultdict(dict)
for r in clips:
    cl[r["selector"]][r["clip_id"]] = r
cliprow = {}
for m in MODES:
    ev = [r for r in cl[m].values() if r["clip_correct"] != ""]
    ok = sum(int(r["clip_correct"]) for r in ev)
    single = sum(int(r["single_valid_only"]) for r in ev)
    cliprow[m] = (len(ev), ok, len(ev) - ok, 39 - len(ev), ok / len(ev) if ev else 0, single)
print(f"| Clip-level evaluable | {' | '.join(str(cliprow[m][0]) for m in MODES)} |")
print(f"| Clip-level correct | {' | '.join(str(cliprow[m][1]) for m in MODES)} |")
print(f"| Clip-level accuracy | {' | '.join(f'{cliprow[m][4]:.1%}' for m in MODES)} |")

sw = {}
for m in MODES:
    vals = [float(r["switch_rate"]) for r in cl[m].values() if r["switch_rate"] != ""]
    sw[m] = (float(np.median(vals)), float(np.mean(vals)), sum(1 for v in vals if v > 0.10), len(vals))
print(f"| Median switching | {' | '.join(f'{sw[m][0]:.1%}' for m in MODES)} |")
print(f"| Mean switching | {' | '.join(f'{sw[m][1]:.1%}' for m in MODES)} |")
print(f"| Clips >10% switching | {' | '.join(f'{sw[m][2]}/{sw[m][3]}' for m in MODES)} |")

# IoU>=0.5 보조 지표
print("\n  [보조] selected box vs GT box IoU >= 0.5 비율")
for m in MODES:
    v = [r for r in by_mode[m] if r["correct"] != ""]
    hit = sum(1 for r in v if float(r["selected_iou"]) >= 0.5)
    exact = sum(int(r["correct"]) for r in v)
    print(f"    {LABEL[m]:12s} IoU>=0.5 {hit}/{len(v)} ({hit/len(v):.1%})   index일치 {exact}/{len(v)} ({exact/len(v):.1%})")

print("\n## 4. Baseline 대비 변화")
for m in ("A", "B"):
    for tag, k in (("전체", "all"), ("multi-cand", "multi")):
        b, x = rows["baseline"][k], rows[m][k]
        d = x[3] - b[3]
        rel = 0.0 if b[3] == 0 else -d / b[3]
        print(f"  {LABEL[m]:12s} [{tag:10s}] wrong-rate {b[3]:.1%} -> {x[3]:.1%} "
              f"({d:+.1%}p, relative {rel:+.1%})   correct {b[1]} -> {x[1]} ({x[1]-b[1]:+d})")
b, x = rows["A"]["all"], rows["B"]["all"]
print(f"  B vs A       [전체      ] wrong-rate {b[3]:.1%} -> {x[3]:.1%} "
      f"({x[3]-b[3]:+.1%}p)   correct {b[1]} -> {x[1]} ({x[1]-b[1]:+d})")
b, x = rows["A"]["multi"], rows["B"]["multi"]
print(f"  B vs A       [multi-cand] wrong-rate {b[3]:.1%} -> {x[3]:.1%} "
      f"({x[3]-b[3]:+.1%}p)   correct {b[1]} -> {x[1]} ({x[1]-b[1]:+d})")

print("\n## 5. Error transition")
idx = {m: {key(r): r for r in by_mode[m]} for m in MODES}
trans = defaultdict(list)
for k, rb in idx["baseline"].items():
    if rb["correct"] == "":
        continue
    cb, ca, cB = int(rb["correct"]), int(idx["A"][k]["correct"]), int(idx["B"][k]["correct"])
    if not cb and ca: trans["baseline_wrong_A_correct"].append(k)
    if not cb and cB: trans["baseline_wrong_B_correct"].append(k)
    if cb and not ca: trans["baseline_correct_A_wrong"].append(k)
    if cb and not cB: trans["baseline_correct_B_wrong"].append(k)
    if not ca and cB: trans["A_wrong_B_correct"].append(k)
    if ca and not cB: trans["A_correct_B_wrong"].append(k)
for name in ("baseline_wrong_A_correct", "baseline_wrong_B_correct",
             "baseline_correct_A_wrong", "baseline_correct_B_wrong",
             "A_wrong_B_correct", "A_correct_B_wrong"):
    print(f"  {name:30s} {len(trans[name]):2d}   {[f'{c}@{r}' for c,r in trans[name]]}")

# 전이 상세 CSV
det = []
for name, keys in trans.items():
    for k in keys:
        rb, ra, rB = idx["baseline"][k], idx["A"][k], idx["B"][k]
        det.append({
            "transition": name, "clip_id": k[0], "ratio": k[1], "frame": rb["frame"],
            "gt_box_index": rb["gt_box_index"], "num_candidates": rb["num_candidates"],
            "num_candidates_ge50": rb["num_candidates_ge50"],
            "baseline_box": rb["selected_box_index"], "A_box": ra["selected_box_index"],
            "B_box": rB["selected_box_index"],
            "baseline_iou": rb["selected_iou"], "A_iou": ra["selected_iou"], "B_iou": rB["selected_iou"],
            "A_centrality": ra["centrality"], "A_size": ra["size"],
            "B_centrality": rB["centrality"], "B_size": rB["size"], "B_continuity": rB["continuity"],
        })
if det:
    with open(OUT / "selector_eval_transitions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(det[0])); w.writeheader(); w.writerows(det)

print("\n## 6. Known clips (Phase A에서 이미 본 4개)")
print(f"  {'clip':14s} {'ratio':6s} {'cand':>4s} {'GT':>3s} {'base':>5s} {'A':>3s} {'B':>3s}   correct(b/A/B)")
for cid in sorted(KNOWN):
    for ratio in ("0.20", "0.50", "0.80"):
        k = (cid, ratio)
        rb, ra, rB = idx["baseline"][k], idx["A"][k], idx["B"][k]
        g = rb["gt_box_index"] if rb["gt_box_index"] != "" else "null"
        cc = "".join("-" if r["correct"] == "" else ("O" if int(r["correct"]) else "X")
                     for r in (rb, ra, rB))
        print(f"  {cid:14s} {ratio:6s} {rb['num_candidates']:>4s} {g:>3s} "
              f"{rb['selected_box_index']:>5s} {ra['selected_box_index']:>3s} "
              f"{rB['selected_box_index']:>3s}   {cc}")

print("\n## 7. Independence sensitivity (4개 known clip 제외)")
print(f"  {'selector':12s} {'전체 97':>22s} {'known 제외':>22s}")
for m in MODES:
    a = stats(by_mode[m])
    e = stats(by_mode[m], lambda r: r["clip_id"] not in KNOWN)
    print(f"  {LABEL[m]:12s} {a[1]}/{a[0]} acc {a[4]:6.1%} wrong {a[3]:6.1%}"
          f"   {e[1]}/{e[0]} acc {e[4]:6.1%} wrong {e[3]:6.1%}")
print(f"  {'':12s} {'multi-cand 64':>22s} {'known 제외':>22s}")
for m in MODES:
    a = stats(by_mode[m], lambda r: int(r["num_candidates"]) >= 2)
    e = stats(by_mode[m], lambda r: int(r["num_candidates"]) >= 2 and r["clip_id"] not in KNOWN)
    print(f"  {LABEL[m]:12s} {a[1]}/{a[0]} acc {a[4]:6.1%} wrong {a[3]:6.1%}"
          f"   {e[1]}/{e[0]} acc {e[4]:6.1%} wrong {e[3]:6.1%}")

print("\n  [참고] clip-level: 평가 불가 clip / valid 1개뿐인 clip")
for m in MODES:
    print(f"    {LABEL[m]:12s} 평가가능 {cliprow[m][0]}/39  평가불가 {cliprow[m][3]}  "
          f"valid 1개뿐 {cliprow[m][5]}")
