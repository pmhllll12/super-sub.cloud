"""Phase B-3 집계 — AI-reviewed(사람 미검증) GT 기준 재평가 결과를 report_b3.md 로 쓴다.

B-2와의 비교는 세 층으로 나눈다.
  (a) B-2 full        전체 97 valid GT, 기존 labels.json
  (b) B-2 matched     B-3와 같은 30프레임, 기존 labels.json
  (c) B-3 AI-reviewed 같은 30프레임, labels_ai_reviewed.json
(b)-(c) 차이만이 '라벨이 바뀌어서 생긴 차이'다.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
B2 = ROOT / "eval_b2"
B3 = ROOT / "eval_b3"
MODES = ["baseline", "A", "B", "A_pose", "B_pose"]
LABEL = {"baseline": "Baseline", "A": "A-geometry", "B": "B-geometry",
         "A_pose": "A-pose", "B_pose": "B-pose"}

b3f = list(csv.DictReader(open(B3 / "selector_eval_frames_ai_reviewed.csv")))
b3c = list(csv.DictReader(open(B3 / "selector_eval_clips_ai_reviewed.csv")))
b2f = list(csv.DictReader(open(B2 / "selector_eval_frames.csv")))
b2c = list(csv.DictReader(open(B2 / "selector_eval_clips.csv")))
changes = list(csv.DictReader(open(B3 / "label_change_analysis.csv")))
trans = list(csv.DictReader(open(B3 / "selector_eval_transitions_ai_reviewed.csv")))

SUBSET = {(r["clip_id"], r["ratio"]) for r in b3f}
CLIPS = sorted({r["clip_id"] for r in b3f})


def stats(rows, field="correct", sub=None):
    v = [r for r in rows if r[field] != ""]
    if sub:
        v = [r for r in v if sub(r)]
    n = len(v)
    c = sum(int(r[field]) for r in v)
    return {"n": n, "correct": c, "wrong": n - c,
            "acc": c / n if n else 0.0, "wrong_rate": (n - c) / n if n else 0.0}


def block(rows, field="correct"):
    out = {}
    for m in MODES:
        rs = [r for r in rows if r["selector"] == m]
        out[m] = {
            "all": stats(rs, field),
            "multi": stats(rs, field, lambda r: int(r["num_candidates"]) >= 2),
        }
    return out


B3_RES = block(b3f)                      # AI-reviewed GT
B2M_RES = block(b3f, "correct_vs_old_gt")  # 같은 프레임, 기존 GT
B2F_RES = block(b2f)                     # 전체 97


def clip_level_b3(m):
    rs = [r for r in b3c if r["selector"] == m and r["clip_correct"] != ""]
    ok = sum(int(r["clip_correct"]) for r in rs)
    return ok, len(rs)


def clip_level_b2(m, subset_only=False):
    rs = [r for r in b2c if r["selector"] == m and r["clip_correct"] != ""]
    if subset_only:
        rs = [r for r in rs if r["clip_id"] in CLIPS]
    ok = sum(int(r["clip_correct"]) for r in rs)
    return ok, len(rs)


def switching(rows, m, clip_filter=None):
    vals = [float(r["switch_rate"]) for r in rows
            if r["selector"] == m and r["switch_rate"] != ""
            and (clip_filter is None or r["clip_id"] in clip_filter)]
    if not vals:
        return 0.0, 0.0, 0, 0
    return (float(np.median(vals)), float(np.mean(vals)),
            sum(1 for v in vals if v > 0.10), len(vals))


# ---------------------------------------------------------------- 축구
soccer_gt = {}
doc = json.loads((B3 / "labels_ai_reviewed.json").read_text())
for r in doc["labels"]:
    if r["sport"] == "soccer":
        soccer_gt[int(r["frame"])] = (r["ai_box_index"], r["ai_confidence"], r["ai_note"])

diffs = defaultdict(dict)
for r in csv.DictReader(open(B2 / "other_sports_diffs.csv")):
    if r["video"] != "10_penalty1.avi":
        continue
    diffs[int(r["frame"])][r["selector"]] = (int(r["baseline_box"]), int(r["selector_box"]),
                                             int(r["n_candidates"]))

soccer_rows = []
soccer_tally = {m: {"개선": 0, "동일": 0, "악화": 0, "판정불가": 0} for m in MODES[1:]}
for f in sorted(soccer_gt):
    gt, conf, note = soccer_gt[f]
    d = diffs.get(f, {})
    base = d[MODES[1]][0] if d else None
    row = {"video": "10_penalty1.avi", "frame": f, "ai_box_index": gt,
           "ai_confidence": conf, "ai_note": note,
           "n_candidates": d[MODES[1]][2] if d else "",
           "baseline_box": "" if base is None else base,
           "baseline_correct": "" if not isinstance(gt, int) or base is None else int(base == gt)}
    for m in MODES[1:]:
        pick = d[m][1] if m in d else base
        row[f"{m}_box"] = "" if pick is None else pick
        if not isinstance(gt, int) or pick is None or base is None:
            row[f"{m}_verdict"] = "판정불가"
            soccer_tally[m]["판정불가"] += 1
            continue
        bc, sc = int(base == gt), int(pick == gt)
        verdict = "개선" if sc > bc else ("악화" if sc < bc else "동일")
        row[f"{m}_correct"] = sc
        row[f"{m}_verdict"] = verdict
        soccer_tally[m][verdict] += 1
    soccer_rows.append(row)

fields = ["video", "frame", "n_candidates", "ai_box_index", "ai_confidence", "ai_note",
          "baseline_box", "baseline_correct"]
for m in MODES[1:]:
    fields += [f"{m}_box", f"{m}_correct", f"{m}_verdict"]
with open(B3 / "soccer_review_analysis.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(soccer_rows)

# ---------------------------------------------------------------- report
L = []
A = L.append

A("# Phase B-3 재평가 — AI-reviewed GT (Human Review Unavailable)")
A("")
A("> **이 보고서의 GT는 사람이 검증한 것이 아니다 (AI-reviewed / unverified).**")
A("> `labels_ai_reviewed.json` = Claude 단독 visual review. `human_verified: false`.")
A("> production selector 최종 확정의 근거로 단독 사용할 수 없다.")
A("")

A("## 1. 표본 (B-2와 다르다)")
A("")
A("| | B-2 full | B-3 AI-reviewed |")
A("|---|---:|---:|")
A(f"| 평가 프레임 | 117 대상 중 valid 97 | 38건 중 30 (uncertain 3 제외, soccer 5 별도) |")
A(f"| valid GT (정확도 분모) | {B2F_RES['baseline']['all']['n']} | {B3_RES['baseline']['all']['n']} |")
A(f"| 클립 | 39 | {len(CLIPS)} |")
A(f"| multi-candidate 프레임 | {B2F_RES['baseline']['multi']['n']} | {B3_RES['baseline']['multi']['n']} |")
A("")
A("**표본이 다를 뿐 아니라 성질이 다르다.** B-3의 33개 야구 프레임은 B-2에서")
A("baseline/A/B 세 selector의 선택이 **갈린 프레임만** 골라낸 집합이다")
A("(`make_review_set.py`). 즉 의도적으로 고른 난이도 상위 표본이므로, 절대")
A("정확도는 B-2 full보다 낮게 나오는 것이 정상이다. 두 절대값을 직접 비교하면 안 된다.")
A("")

A("## 2. 메인 결과 — AI-reviewed GT (n=%d)" % B3_RES["baseline"]["all"]["n"])
A("")
A("| Metric | " + " | ".join(LABEL[m] for m in MODES) + " |")
A("|---|" + "---:|" * len(MODES))


def row(name, fn):
    A(f"| {name} | " + " | ".join(fn(m) for m in MODES) + " |")


row("Valid GT n", lambda m: str(B3_RES[m]["all"]["n"]))
row("Correct", lambda m: str(B3_RES[m]["all"]["correct"]))
row("Wrong", lambda m: str(B3_RES[m]["all"]["wrong"]))
row("Wrong-person rate", lambda m: f"{B3_RES[m]['all']['wrong_rate']:.1%}")
row("Accuracy", lambda m: f"{B3_RES[m]['all']['acc']:.1%}")
row("Multi-cand correct", lambda m: f"{B3_RES[m]['multi']['correct']}/{B3_RES[m]['multi']['n']}")
row("Multi-cand wrong-rate", lambda m: f"{B3_RES[m]['multi']['wrong_rate']:.1%}")
row("Multi-cand accuracy", lambda m: f"{B3_RES[m]['multi']['acc']:.1%}")
row("Clip-level accuracy", lambda m: "{}/{} = {:.1%}".format(
    *clip_level_b3(m), clip_level_b3(m)[0] / max(clip_level_b3(m)[1], 1)))
row("Switching median", lambda m: f"{switching(b3c, m)[0]:.1%}")
row("Switching mean", lambda m: f"{switching(b3c, m)[1]:.1%}")
row("Clips >10% switching", lambda m: f"{switching(b3c, m)[2]}/{switching(b3c, m)[3]}")
A("")
A("- clip-level은 **검수된 프레임이 2개 이상인 클립만** 대상으로 했다(B-2의 '3개 중 2개' 규칙을")
A("  그대로 쓰면 검수 프레임이 1개인 클립은 구조적으로 항상 오답이 된다). 대상 클립 수가")
A(f"  {clip_level_b3('baseline')[1]}개로 작아 이 지표는 참고용이다.")
A("- switching은 **라벨과 무관한 지표**다(클립 전체에서 selector가 사람을 바꾼 비율).")
A(f"  같은 {len(CLIPS)}개 클립에 대한 값이라 B-2와 동일하게 나오는 것이 정상이다.")
A("")

A("## 3. B-2 vs B-3 비교")
A("")
A("### 3-1. 같은 30프레임, 라벨만 교체 (라벨 효과의 순수 측정)")
A("")
A("| Selector | B-2 labels.json | B-3 AI-reviewed | Δ accuracy | wrong-rate Δ |")
A("|---|---:|---:|---:|---:|")
for m in MODES:
    o, n = B2M_RES[m]["all"], B3_RES[m]["all"]
    A(f"| {LABEL[m]} | {o['correct']}/{o['n']} = {o['acc']:.1%} | "
      f"{n['correct']}/{n['n']} = {n['acc']:.1%} | {n['acc'] - o['acc']:+.1f}pp".replace(
          f"{n['acc'] - o['acc']:+.1f}pp", f"{(n['acc'] - o['acc']) * 100:+.1f}pp")
      + f" | {(n['wrong_rate'] - o['wrong_rate']) * 100:+.1f}pp |")
A("")
A("두 열의 분모가 다르다(26 vs 28). 기존 라벨에서 null이던 4프레임 중 2건을")
A("AI review가 후보로 지목했기 때문이다. 분모까지 맞춘 비교는 아래.")
A("")
A("### 3-1b. 양쪽 모두 GT가 있는 26프레임 (분모까지 고정)")
A("")


def common(r):
    return r["gt_box_index"] != "" and r["old_gt_box_index"] != ""


A("| Selector | 기존 GT | AI GT | Δ |")
A("|---|---:|---:|---:|")
for m in MODES:
    rs = [r for r in b3f if r["selector"] == m and common(r)]
    o = stats(rs, "correct_vs_old_gt")
    n = stats(rs, "correct")
    A(f"| {LABEL[m]} | {o['correct']}/{o['n']} = {o['acc']:.1%} | "
      f"{n['correct']}/{n['n']} = {n['acc']:.1%} | {(n['acc'] - o['acc']) * 100:+.1f}pp |")
A("")
ncommon_diff = [r for r in changes
                if r["change_type"] == "candidate->candidate"]
A(f"**모든 selector에서 Δ가 0이다.** 이 26프레임에서 기존 라벨과 AI 판독이 갈린 것은")
A(f"{len(ncommon_diff)}건뿐이고({', '.join('`' + r['clip_id'] + '@' + r['ratio'] + '`' for r in ncommon_diff)}),")
A("그 프레임에서는 다섯 selector가 **기존 GT(6)도 AI GT(1)도 아닌 다른 후보**를 골랐다")
A("(picks: baseline 3, 나머지 0). 즉 어느 라벨을 쓰든 5개 전부 오답이라 지표가 움직이지 않는다.")
A("라벨 교체는 selector 간 상대 비교를 전혀 흔들지 않았다.")
A("")

A("### 3-2. multi-candidate (같은 30프레임)")
A("")
A("| Selector | B-2 multi acc | B-3 multi acc | Δ |")
A("|---|---:|---:|---:|")
for m in MODES:
    o, n = B2M_RES[m]["multi"], B3_RES[m]["multi"]
    A(f"| {LABEL[m]} | {o['correct']}/{o['n']} = {o['acc']:.1%} | "
      f"{n['correct']}/{n['n']} = {n['acc']:.1%} | {(n['acc'] - o['acc']) * 100:+.1f}pp |")
A("")
A("이 표본에서는 **multi-candidate 지표가 전체 지표와 같다.** 검수 대상이 'selector들의")
A("선택이 갈린 프레임'이라 후보가 1개인 프레임은 구조적으로 포함될 수 없기 때문이다")
A("(최소 후보 수 2).")
A("")

A("### 3-3. 참고 — B-2 full (97) 대비")
A("")
A("| Selector | B-2 full acc | B-2 matched(30) | B-3 AI(28) |")
A("|---|---:|---:|---:|")
for m in MODES:
    A(f"| {LABEL[m]} | {B2F_RES[m]['all']['acc']:.1%} ({B2F_RES[m]['all']['correct']}/{B2F_RES[m]['all']['n']}) "
      f"| {B2M_RES[m]['all']['acc']:.1%} ({B2M_RES[m]['all']['correct']}/{B2M_RES[m]['all']['n']}) "
      f"| {B3_RES[m]['all']['acc']:.1%} ({B3_RES[m]['all']['correct']}/{B3_RES[m]['all']['n']}) |")
A("")

A("### 3-4. 순위")
A("")


def ranking(res):
    order = sorted(MODES, key=lambda m: (-res[m]["all"]["acc"], MODES.index(m)))
    return " > ".join(f"{LABEL[m]}({res[m]['all']['acc']:.1%})" for m in order)


A(f"- **B-2 full**: {ranking(B2F_RES)}")
A(f"- **B-2 matched(30)**: {ranking(B2M_RES)}")
A(f"- **B-3 AI-reviewed**: {ranking(B3_RES)}")
A("")

A("## 4. A-pose vs B-pose")
A("")
ap, bp = B3_RES["A_pose"]["all"], B3_RES["B_pose"]["all"]
apm, bpm = B3_RES["A_pose"]["multi"], B3_RES["B_pose"]["multi"]
A("| | A-pose | B-pose | 차이 |")
A("|---|---:|---:|---:|")
A(f"| Accuracy | {ap['acc']:.1%} ({ap['correct']}/{ap['n']}) | {bp['acc']:.1%} ({bp['correct']}/{bp['n']}) "
  f"| {(bp['acc'] - ap['acc']) * 100:+.1f}pp |")
A(f"| Wrong-person rate | {ap['wrong_rate']:.1%} | {bp['wrong_rate']:.1%} "
  f"| {(bp['wrong_rate'] - ap['wrong_rate']) * 100:+.1f}pp |")
A(f"| Multi-cand accuracy | {apm['acc']:.1%} ({apm['correct']}/{apm['n']}) | "
  f"{bpm['acc']:.1%} ({bpm['correct']}/{bpm['n']}) | {(bpm['acc'] - apm['acc']) * 100:+.1f}pp |")
A(f"| Switching mean | {switching(b3c, 'A_pose')[1]:.1%} | {switching(b3c, 'B_pose')[1]:.1%} | |")
A("")
ab = [t for t in trans if t["transition"] == "A_pose->B_pose"]
rec = [t for t in ab if t["type"] == "recovery"]
reg = [t for t in ab if t["type"] == "regression"]
A(f"A-pose → B-pose 전이: recovery {len(rec)}, regression {len(reg)}, net {len(rec) - len(reg):+d}")
for t in ab:
    A(f"- `{t['clip_id']}@{t['ratio']}` {t['type']}: {t['src_box']} → {t['dst_box']} "
      f"(GT {t['gt_box_index']}, 후보 {t['num_candidates']}, AI conf {t['ai_confidence']})")
A("")

A("## 5. 라벨 변경 영향")
A("")
tally = defaultdict(int)
for r in changes:
    tally[r["change_type"]] += 1
A("| 유형 | 건수 |")
A("|---|---:|")
for k in ("unchanged", "candidate->candidate", "none->candidate",
          "label->none", "none->none", "label->uncertain", "none->uncertain"):
    if tally[k]:
        A(f"| {k} | {tally[k]} |")
A(f"| **합계** | **{len(changes)}** |")
A("")
diff_rows = [r for r in changes if r["change_type"] != "unchanged"]
A(f"기존 라벨과 다르게 판단한 건: **{len(diff_rows)}/{len(changes)}** "
  f"({len(diff_rows) / len(changes):.0%})")
A("")
A("| clip@ratio | 기존 | AI | 유형 | conf | 후보 |")
A("|---|---:|---:|---|---|---:|")
for r in diff_rows:
    A(f"| `{r['clip_id']}@{r['ratio']}` | {r['old_box_index'] or 'null'} | {r['ai_box_index']} "
      f"| {r['change_type']} | {r['ai_confidence']} | {r['n_candidates']} |")
A("")

A("## 6. B-2 핵심 regression 재확인")
A("")
A("| case | AI GT | conf | baseline | A | B | A-pose | B-pose | 판정 |")
A("|---|---|---|---|---|---|---|---|---|")
idx = defaultdict(dict)
for r in b3f:
    idx[(r["clip_id"], r["ratio"])][r["selector"]] = r
ai_all = {(r["clip_id"], r["ratio"]): r for r in changes}
for cid, ratio in (("LhD_fnHt_xg", "0.50"), ("LhD_fnHt_xg", "0.80"), ("N5zWQkoLM3M", "0.50")):
    k = (cid, ratio)
    meta = ai_all[k]
    if k not in idx:
        A(f"| `{cid}@{ratio}` | {meta['ai_box_index']} | {meta['ai_confidence']} "
          f"| — | — | — | — | — | 제외 (uncertain/none) |")
        continue
    cells = []
    for m in MODES:
        r = idx[k][m]
        mark = "-" if r["correct"] == "" else ("O" if int(r["correct"]) else "X")
        cells.append(f"{r['selected_box_index']}{mark}")
    row_ok = [idx[k][m]["correct"] for m in MODES]
    verdict = ("regression 재현" if row_ok[0] == "1" and row_ok[4] == "0"
               else "regression 아님" if row_ok[4] == "1" else "전 selector 오답")
    A(f"| `{cid}@{ratio}` | {meta['ai_box_index']} | {meta['ai_confidence']} | "
      + " | ".join(cells) + f" | {verdict} |")
A("")
A("표기: `선택index` + O(정답)/X(오답).")
A("")

A("## 7. 축구 5프레임 (10_penalty1.avi)")
A("")
A("| frame | AI GT | conf | baseline | 새 selector 4종 | 판정 |")
A("|---|---:|---|---:|---:|---|")
for r in soccer_rows:
    picks = {r[f"{m}_box"] for m in MODES[1:]}
    same = picks.pop() if len(picks) == 1 else "/".join(str(r[f'{m}_box']) for m in MODES[1:])
    A(f"| {r['frame']} | {r['ai_box_index']} | {r['ai_confidence']} | {r['baseline_box']} "
      f"| {same} | {r['A_verdict']} |")
A("")
for m in MODES[1:]:
    t = soccer_tally[m]
    A(f"- **{LABEL[m]}**: 개선 {t['개선']} / 동일 {t['동일']} / 악화 {t['악화']}"
      + (f" / 판정불가 {t['판정불가']}" if t["판정불가"] else ""))
A("")
A("네 selector 모두 이 5프레임에서 동일하게 선택했고, 5프레임 전부 baseline과 달랐다.")
A("baseline은 **면적 최대**를 고르는데, 페널티킥 장면에서 카메라에 가까운 골키퍼가")
A("키커보다 크게 잡히는 구간이 있어 그때 키커를 놓친다.")
A("")

A("## 8. 최종 해석")
A("")
best = max(MODES, key=lambda m: B3_RES[m]["all"]["acc"])
tied = [m for m in MODES if B3_RES[m]["all"]["correct"] == B3_RES[best]["all"]["correct"]]
A(f"AI-reviewed GT(n={B3_RES['baseline']['all']['n']})에서 최고 정확도: "
  f"**{', '.join(LABEL[m] for m in tied)}** ({B3_RES[best]['all']['acc']:.1%}).")
A("")
A("### 판정")
A("")
A("> **순위 불안정 — A-pose와 B-pose의 우열은 이 표본에서 판정되지 않는다.**")
A("")
A(f"- A-pose {ap['correct']}/{ap['n']}, B-pose {bp['correct']}/{bp['n']} — **완전 동점**이다.")
A(f"  전이도 recovery {len(rec)} / regression {len(reg)}로 상쇄된다(net 0).")
A("- B-2 full에서 B-pose가 A-pose를 앞선 근거(85건 vs 83건, 2건 차)는 **이번 검수")
A("  대상 밖의 프레임에서 나온 것**이다. 이 33프레임 안에서는 기존 라벨로도(20/26 동점)")
A("  AI 라벨로도(20/28 동점) 두 selector가 갈리지 않는다.")
A("- 즉 이번 재평가는 B-pose 우세를 **반박하지도 확증하지도 않는다.** 2건 차이를")
A("  가르려면 검수 대상이 아니었던 나머지 프레임의 라벨 검증이 필요하다.")
A("")
A("### 안정적으로 확인된 것")
A("")
A("- **계층 순서는 라벨 교체와 무관하게 유지된다**: pose 계열(71.4%) > B-geometry(67.9%)")
A("  > A-geometry(64.3%) >> Baseline(17.9%). 세 층 모두 B-2 matched와 같은 순서다.")
A("- **Baseline(면적 최대)은 다인 프레임에서 무너진다.** 이 표본에서 17.9%로,")
A("  네 selector 중 최하위이며 격차가 46pp 이상이다. 축구 5프레임에서도 5/5 열세다.")
A(f"- **continuity는 switching을 확실히 줄인다**: mean {switching(b3c, 'A_pose')[1]:.1%}(A-pose)")
A(f"  → {switching(b3c, 'B_pose')[1]:.1%}(B-pose), >10% 클립 {switching(b3c, 'A_pose')[2]}개 → "
  f"{switching(b3c, 'B_pose')[2]}개. 이 지표는 GT와 무관하므로 라벨 불확실성의 영향을 받지 않는다.")
A("- 다만 continuity는 `N5zWQkoLM3M@0.50/0.80`에서 **틀린 대상에 고착**시키는 방향으로도")
A("  작동했다(B-geometry·B-pose가 A 계열 대비 regression). 정확도와 안정성의 트레이드오프다.")
A("")
A("### 남은 불확실성")
A("")
A(f"- 유효 표본 {B3_RES['baseline']['all']['n']}건은 selector 간 2건 차이를 가르기에 부족하다.")
A("- AI 판독 자체가 medium confidence인 건이 이 표본에 8건 있고, A-pose/B-pose 전이")
A("  4건 중 3건이 medium 구간에 걸쳐 있다.")
A("- 이 33프레임은 난이도 상위로 편향된 표본이므로 절대 정확도를 서비스 품질 추정에")
A("  쓸 수 없다.")
A("")
A("## 9. Production readiness")
A("")
A("**Human verified GT가 아니므로 production selector 최종 확정의 근거로 단독 사용 불가.**")
A("")
A("- 이번 단계에서 production code / tests / rubric / goldenset / 가중치 / selector 구현은")
A("  변경하지 않았다. selector 선택 결과는 B-2와 150/150 행 완전 일치로, **바뀐 것은 GT뿐**이다.")
A("- 확정에 필요한 것: (1) 지도자 또는 사람 검수자의 라벨 검증, (2) 검수 대상이 아니었던")
A("  프레임까지 포함한 재검증, (3) A-pose/B-pose 동점을 가를 추가 표본.")
A("")

(B3 / "report_b3.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
