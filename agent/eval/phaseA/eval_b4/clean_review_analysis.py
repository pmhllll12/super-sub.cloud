"""B-4 사후 비교 — clean independent AI review vs 기존 GT/AI/selector.

이 스크립트는 **읽기 전용 비교**만 한다. labels.json·selector·weights·기존 산출물을
수정하지 않는다. clean review 결과를 GT로 승격하지 않는다.
"""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

ROOT = Path("/mnt/d/supersub-phaseA")
B4 = ROOT / "eval_b4"

# 합의 프레임(불일치 아님)에서 두 selector가 똑같이 얻은 점수 — B-4에서 확정
BASE_CORRECT, BASE_N = 81, 91

CASE = {  # case -> (clip_id, frame)
    "T0-01": ("3USSmzO001k", 119), "T0-02": ("5-jBTNp5IQA", 75),
    "T0-03": ("IeDin6oB-IY", 75), "T0-04": ("N5zWQkoLM3M", 75),
    "T0-05": ("N5zWQkoLM3M", 119), "T0-06": ("X6dC9pu5H3k", 107),
    "T0-07": ("sYl2jCqsSKo", 119),
}

# ---- selector 선택값·기존 GT (읽기 전용) ---------------------------------
dis = {}
for r in csv.DictReader(open(B4 / "ab_disagreement_frames.csv")):
    dis[(r["clip_id"], int(r["frame"]))] = r

old_gt = {}
for r in json.loads((ROOT / "labeling" / "labels.json").read_text())["frames"]:
    old_gt[(r["clip_id"], r["ratio"])] = r["box_index"]

# ---- 판독 결과 ------------------------------------------------------------
clean0 = {r["case"]: r for r in csv.DictReader(open(B4 / "tier0_ai_clean_blind_review.csv"))}
clean1 = list(csv.DictReader(open(B4 / "tier1_ai_clean_blind_review.csv")))
old0 = {(r["clip_id"], int(r["frame"])): r
        for r in csv.DictReader(open(B4 / "tier0_ai_blind_review.csv"))}
old1 = {(r["clip_id"], int(r["frame"])): r
        for r in csv.DictReader(open(B4 / "tier1_ai_blind_review.csv"))}


def picks(case):
    d = dis[CASE[case]]
    return int(d["a_pose_box"]), int(d["b_pose_box"])


def gt_of(case):
    d = dis[CASE[case]]
    return d["old_gt"] if d["old_gt"] != "" else None


def outcome(label, a, b):
    """한 프레임의 승자. uncertain/none/빈값은 평가 제외."""
    if label in (None, "", "uncertain", "none"):
        return "excluded"
    v = int(label)
    if v == b:
        return "B"
    if v == a:
        return "A"
    return "neither"


# ================================================================ 3. 두 AI 비교
cmp_rows = []
for case in sorted(CASE):
    cid, f = CASE[case]
    c, o = clean0[case], old0[(cid, f)]
    cmp_rows.append({
        "case": case, "clip_frame": f"{cid}@{f}", "n_candidates": c["n_candidates"],
        "old_AI_result": o["ai_box_index"], "clean_AI_result": c["human_box_index"],
        "old_confidence": o["confidence"], "clean_confidence": c["confidence"],
        "old_blind_status": o["blind_status"], "clean_blind_status": "clean_independent",
        "changed": int(o["ai_box_index"] != c["human_box_index"]),
        "note": c["human_note"],
    })
with open(B4 / "clean_review_comparison.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(cmp_rows[0])); w.writeheader(); w.writerows(cmp_rows)

# ================================================================ 4. GT 비교
gt_rows = []
for case in sorted(CASE):
    cid, f = CASE[case]
    g, c = gt_of(case), clean0[case]["human_box_index"]
    if g is None:
        t = "GT none vs AI candidate" if c.isdigit() else f"GT none vs AI {c}"
        agree = ""
    elif c == "uncertain":
        t, agree = "GT candidate vs AI uncertain", 0
    elif c == "none":
        t, agree = "GT candidate vs AI none", 0
    elif int(c) == int(g):
        t, agree = "candidate index 동일", 1
    else:
        t, agree = "candidate index 다름", 0
    gt_rows.append({"case": case, "clip_frame": f"{cid}@{f}",
                    "existing_gt": "null" if g is None else g,
                    "clean_ai_result": c, "agreement": agree, "disagreement_type": t,
                    "clean_confidence": clean0[case]["confidence"]})
with open(B4 / "clean_review_gt_comparison.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(gt_rows[0])); w.writeheader(); w.writerows(gt_rows)

# ================================================================ 5. sensitivity
def tally(labels):
    a = b = valid = 0
    for case in sorted(CASE):
        ap, bp = picks(case)
        o = outcome(labels.get(case), ap, bp)
        if o == "excluded":
            continue
        valid += 1
        a += o == "A"
        b += o == "B"
    return valid, a, b


SCEN = {
    "A. 기존 labels.json": {c: gt_of(c) for c in CASE},
    "B. 기존 AI-reviewed(오염 포함)": {
        c: old0[CASE[c]]["ai_box_index"] for c in CASE},
    "C. clean independent AI review": {
        c: clean0[c]["human_box_index"] for c in CASE},
}
sens_rows = []
for name, lab in SCEN.items():
    v, a, b = tally(lab)
    A, B, N = BASE_CORRECT + a, BASE_CORRECT + b, BASE_N + v
    sens_rows.append({"scenario": name, "valid_count": v, "a_wins": a, "b_wins": b,
                      "neither_or_excluded": 7 - v + (v - a - b),
                      "a_correct": A, "b_correct": B, "denominator": N,
                      "a_accuracy": f"{A/N:.4f}", "b_accuracy": f"{B/N:.4f}",
                      "margin_b_minus_a": B - A})
with open(B4 / "clean_review_sensitivity.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(sens_rows[0])); w.writeheader(); w.writerows(sens_rows)

# ================================================================ 6. 조합표
CRIT = ["T0-01", "T0-06"]


def grid(base_labels, tag):
    others = {c: base_labels[c] for c in CASE if c not in CRIT}
    v0, a0, b0 = tally({**others, **{c: None for c in CRIT}})
    rows = []
    for k1, k2 in itertools.product(["B", "A", "uncertain"], repeat=2):
        m = (b0 - a0)
        for k in (k1, k2):
            m += 1 if k == "B" else (-1 if k == "A" else 0)
        rows.append({"basis": tag, "T0-01": k1, "T0-06": k2, "margin_b_minus_a": m,
                     "verdict": "B 우세" if m > 0 else ("A 우세" if m < 0 else "동률")})
    return rows, (b0 - a0)


g_gt, m_gt = grid(SCEN["A. 기존 labels.json"], "나머지 5건 = labels.json")
g_cl, m_cl = grid(SCEN["C. clean independent AI review"], "나머지 5건 = clean AI")
with open(B4 / "clean_review_t0_grid.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(g_gt[0])); w.writeheader()
    w.writerows(g_gt + g_cl)

# ================================================================ 7. Tier 1
t1_rows, agree_ab = [], {"A": 0, "B": 0, "neither": 0, "excluded": 0}
old_agree = same = 0
for r in clean1:
    key = (r["clip_id"], int(r["frame"]))
    d = dis[key]
    ap, bp = int(d["a_pose_box"]), int(d["b_pose_box"])
    o = outcome(r["human_box_index"], ap, bp)
    agree_ab[o] += 1
    ov = old1[key]["ai_box_index"] if key in old1 else ""
    same += int(ov == r["human_box_index"])
    old_agree += 1
    t1_rows.append({"case": r["case"], "clip_frame": f'{r["clip_id"]}@{r["frame"]}',
                    "n_candidates": r["n_candidates"],
                    "clean_ai_result": r["human_box_index"],
                    "clean_confidence": r["confidence"],
                    "prior_ai_result": ov,
                    "prior_vs_clean_same": int(ov == r["human_box_index"]),
                    "matches_selector": o if o != "excluded" else "",
                    "note": r["human_note"]})
with open(B4 / "clean_review_tier1_summary.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(t1_rows[0])); w.writeheader(); w.writerows(t1_rows)

# ================================================================ 출력
print("== 3. 두 AI 판독 비교 (Tier 0) ==")
for r in cmp_rows:
    print(f"  {r['case']} {r['clip_frame']:<22} old={r['old_AI_result']:<9} "
          f"clean={r['clean_AI_result']:<9} changed={r['changed']}  ({r['old_blind_status']})")
print(f"  변경된 건: {sum(r['changed'] for r in cmp_rows)}/7")

print("\n== 4. clean AI vs 기존 GT ==")
for r in gt_rows:
    print(f"  {r['case']} {r['clip_frame']:<22} GT={str(r['existing_gt']):<5} "
          f"AI={r['clean_ai_result']:<9} {r['disagreement_type']}")
ag = [r for r in gt_rows if r["agreement"] != ""]
print(f"  일치 {sum(int(r['agreement']) for r in ag)}/{len(ag)} (GT가 null인 1건 제외)")

print("\n== 5. A/B sensitivity ==")
for r in sens_rows:
    print(f"  {r['scenario']:<32} valid {r['valid_count']}  A승 {r['a_wins']}  B승 {r['b_wins']}"
          f"   A {r['a_correct']}/{r['denominator']}={float(r['a_accuracy']):.1%}"
          f"   B {r['b_correct']}/{r['denominator']}={float(r['b_accuracy']):.1%}"
          f"   margin {r['margin_b_minus_a']:+d}")

print(f"\n== 6. T0-01 x T0-06 조합 (나머지 5건 고정) ==")
for tag, g, m in (("labels.json", g_gt, m_gt), ("clean AI", g_cl, m_cl)):
    print(f"  [나머지 5건 = {tag}] 나머지 margin {m:+d}")
    for r in g:
        print(f"    T0-01={r['T0-01']:<9} T0-06={r['T0-06']:<9} margin {r['margin_b_minus_a']:+d}  {r['verdict']}")

print("\n== 7. Tier 1 (53건, 보조 근거) ==")
print(f"  selector 대조: A-pose와 일치 {agree_ab['A']}  B-pose와 일치 {agree_ab['B']}  "
      f"둘 다 아님 {agree_ab['neither']}  판정제외(none/uncertain) {agree_ab['excluded']}")
print(f"  이전 AI 판독과 동일한 건: {same}/53 ({same/53:.0%})")
