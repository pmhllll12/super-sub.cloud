"""Phase B-4 민감도 분석 — B-pose +2 우위가 어떤 라벨에 얼마나 의존하는가.

A-pose와 B-pose는 **불일치 프레임에서만** 점수가 갈린다. B-2 full 97건 중
불일치이면서 GT가 있는 것은 6건뿐이고(+ GT null 1건), 나머지 91건에서는 둘 다
81/91로 완전히 같다. 따라서 순위는 이 7프레임이 전부 결정한다.

라벨 출처를 섞는다는 점을 명시한다: 아래 'AI-reviewed' 시나리오는 91개 합의
프레임은 labels.json을 그대로 두고 7개 불일치 프레임만 AI 판독으로 교체한 것이다.
합의 프레임은 두 selector에 동일하게 기여하므로 순위에는 영향이 없다.

**AI-reviewed 결과는 HUMAN VERIFIED가 아니다.**
"""

from __future__ import annotations

import csv
import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path("/mnt/d/supersub-phaseA")
B4 = ROOT / "eval_b4"

# 합의 프레임(불일치 아님)에서 두 selector가 똑같이 얻은 점수
BASE_CORRECT = 81
BASE_N = 91

# Tier 0 7건 — picks는 eval_b2 selector 출력(결정론), 라벨은 두 출처
CASES = [
    # clip@ratio,               a_pick, b_pick, old_gt, ai_gt, ai_conf, blind?
    ("3USSmzO001k@0.80", 0, 1, 1, 1, "high", False),
    ("5-jBTNp5IQA@0.50", 1, 0, 0, 0, "medium", True),
    ("IeDin6oB-IY@0.50", 0, 4, 4, 4, "high", True),
    ("N5zWQkoLM3M@0.50", 2, 1, 2, 2, "medium", True),
    ("N5zWQkoLM3M@0.80", 2, 1, 2, 2, "medium", True),
    ("X6dC9pu5H3k@0.80", 4, 0, 0, "uncertain", "low", False),
    ("sYl2jCqsSKo@0.80", 1, 0, None, 2, "medium", True),
]
CRITICAL = {"3USSmzO001k@0.80", "X6dC9pu5H3k@0.80"}


def outcome(a_pick, b_pick, gt):
    """한 프레임의 승자. None/uncertain은 평가 제외."""
    if gt is None or gt == "uncertain" or gt == "none":
        return "excluded"
    if gt == b_pick:
        return "B"
    if gt == a_pick:
        return "A"
    return "neither"


def tally(gts):
    a = b = n_valid = 0
    for (name, ap, bp, *_), g in zip(CASES, gts):
        o = outcome(ap, bp, g)
        if o == "excluded":
            continue
        n_valid += 1
        a += o == "A"
        b += o == "B"
    return a, b, n_valid


def fmt(a, b, n_valid):
    A = BASE_CORRECT + a
    B = BASE_CORRECT + b
    N = BASE_N + n_valid
    return (f"A-pose {A}/{N} = {A/N:.1%}   B-pose {B}/{N} = {B/N:.1%}   "
            f"margin {B - A:+d}건")


L = []
P = L.append

P("# Phase B-4 민감도 분석 — B-pose 우위는 무엇에 달려 있는가")
P("")
P("> **AI-reviewed / unverified. HUMAN VERIFIED GT가 아니다.**")
P("> 이 분석으로 production selector를 확정하지 않는다.")
P("")
P("## 0. 구조")
P("")
P(f"- A-pose와 B-pose는 합의 프레임 {BASE_N}건에서 **둘 다 {BASE_CORRECT}/{BASE_N} 동일**하다.")
P("- 두 selector의 점수 차이는 **불일치 7프레임에서만** 발생한다.")
P("- 따라서 순위 문제는 '97건 중 무엇이 맞나'가 아니라 '이 7건의 라벨이 무엇인가'다.")
P("")

P("## 1. Tier 0 7건 — 판독 결과")
P("")
P("| clip@ratio | 후보 | A-pose | B-pose | 기존 GT | AI 판독 | conf | blind |")
P("|---|---:|---:|---:|---:|---:|---|---|")
for name, ap, bp, og, ag, conf, blind in CASES:
    P(f"| `{name}` | | {ap} | {bp} | {og if og is not None else 'null'} | {ag} | {conf} "
      f"| {'B-3 blind' if blind else '**오염**'} |")
P("")
P("`blind` 열의 '오염'은 해당 프레임의 기존 GT와 양쪽 selector 선택을 **판독 전에 이미**")
P("본 상태에서 판독했다는 뜻이다. 두 건 모두 이번 단계에서 처음 판독한 것이고, 하필")
P("가장 중요한 두 건이다. 독립 판독으로 취급할 수 없다.")
P("")

P("## 2. 시나리오별 결과")
P("")
scenarios = [
    ("기존 labels.json 유지", [c[3] for c in CASES]),
    ("AI 판독 적용 (uncertain 제외)", [c[4] for c in CASES]),
    ("오염된 2건 제외, 나머지는 AI 판독",
     [("uncertain" if c[0] in CRITICAL else c[4]) for c in CASES]),
    ("B-3에서 실제 blind 판독한 5건만",
     [(c[4] if c[6] else "uncertain") for c in CASES]),
]
P("| 시나리오 | 유효 | A승 | B승 | 결과 |")
P("|---|---:|---:|---:|---|")
for label, gts in scenarios:
    a, b, nv = tally(gts)
    P(f"| {label} | {nv} | {a} | {b} | {fmt(a, b, nv)} |")
P("")

P("## 3. 핵심 질문 — 두 건에 얼마나 의존하는가")
P("")
others = [c for c in CASES if c[0] not in CRITICAL]
oa = ob = 0
for name, ap, bp, og, ag, conf, blind in others:
    o = outcome(ap, bp, ag)
    oa += o == "A"
    ob += o == "B"
P(f"오염되지 않은 나머지 5건의 AI 판독 결과: **A승 {oa}, B승 {ob} → margin {ob - oa:+d}**")
P("")
P("| 5-jBTNp5IQA@0.50 | IeDin6oB-IY@0.50 | N5zWQkoLM3M@0.50 | N5zWQkoLM3M@0.80 | sYl2jCqsSKo@0.80 |")
P("|---|---|---|---|---|")
P("| B승 | B승 | A승 | A승 | 둘 다 오답 |")
P("")
P(f"**나머지 5건은 정확히 상쇄된다(margin {ob - oa:+d}).**")
P("즉 B-pose의 +2 우위는 `3USSmzO001k@0.80`과 `X6dC9pu5H3k@0.80` **두 건에 100% 의존한다.**")
P("")
P("### 두 건의 모든 조합")
P("")
P("| 3USSmzO001k@0.80 | X6dC9pu5H3k@0.80 | margin | 해석 |")
P("|---|---|---:|---|")
opts = [("B가 정답", "b"), ("A가 정답", "a"), ("둘 다 오답/제외", "x")]
rows_grid = []
for (l1, k1), (l2, k2) in itertools.product(opts, repeat=2):
    m = ob - oa
    for k in (k1, k2):
        m += 1 if k == "b" else (-1 if k == "a" else 0)
    interp = ("B-pose 우세" if m > 0 else "A-pose 우세" if m < 0 else "완전 동률")
    rows_grid.append((l1, l2, m, interp))
    P(f"| {l1} | {l2} | {m:+d} | {interp} |")
P("")
P("- **둘 다 B 정답** → +2 (현재 labels.json이 주장하는 상태)")
P("- **하나만 B 정답** → +1 (이번 AI 판독이 가리키는 상태)")
P("- **둘 다 B 오답(A 정답)** → −2 (**A-pose 우세로 역전**)")
P("- **둘 다 판정 불가** → 0 (완전 동률)")
P("")

P("## 4. 전체 조합 분포 (7건 각각 A/B/판정불가 3가지)")
P("")
dist = Counter()
for combo in itertools.product(["b", "a", "x"], repeat=len(CASES)):
    m = sum(1 if k == "b" else (-1 if k == "a" else 0) for k in combo)
    dist[m] += 1
tot = sum(dist.values())
P("| margin | 조합 수 | 비율 |")
P("|---:|---:|---:|")
for m in sorted(dist):
    P(f"| {m:+d} | {dist[m]} | {dist[m]/tot:.1%} |")
P("")
P(f"7건 전부 미검증이라고 보면 가능한 조합은 {tot}개이고, 그중 **B-pose 우세는 "
  f"{sum(v for k, v in dist.items() if k > 0)/tot:.0%}, 동률 {dist[0]/tot:.0%}, "
  f"A-pose 우세 {sum(v for k, v in dist.items() if k < 0)/tot:.0%}**다. "
  f"현재 근거는 이 분포 안에서 한 점을 고른 것에 불과하다.")
P("")

P("## 5. regression case (별도 유지)")
P("")
P("`N5zWQkoLM3M@0.50` — A-pose 2 정답 / B-pose 1 오답, B-pose continuity 0.828.")
P("독립 판독(B-3, blind)에서도 GT 2로 재확인됐다. B-pose가 f74에서 잘못 획득한")
P("대상을 유지하며 발생한 **stability trade-off의 실증 사례**로 남긴다.")
P("`N5zWQkoLM3M@0.80`도 같은 고착의 연장이며, `LhD_fnHt_xg@0.50/0.80`은 두 selector가")
P("함께 틀리므로 A/B 판별에는 쓸 수 없으나 pose 계열 공통 failure mode로 추적한다.")
P("")

with open(B4 / "tier0_sensitivity.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["scenario", "valid_n", "a_wins", "b_wins", "a_total", "b_total",
                "total_n", "a_acc", "b_acc", "margin"])
    for label, gts in scenarios:
        a, b, nv = tally(gts)
        A, B, N = BASE_CORRECT + a, BASE_CORRECT + b, BASE_N + nv
        w.writerow([label, nv, a, b, A, B, N, round(A / N, 4), round(B / N, 4), B - A])
    w.writerow([])
    w.writerow(["3USSmzO001k@0.80", "X6dC9pu5H3k@0.80", "margin", "interpretation"])
    for r in rows_grid:
        w.writerow([r[0], r[1], r[2], r[3]])

with open(B4 / "tier0_ai_review.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["clip_ratio", "a_pose_box", "b_pose_box", "old_gt", "ai_box_index",
                "ai_confidence", "blind_status", "outcome_old", "outcome_ai"])
    for name, ap, bp, og, ag, conf, blind in CASES:
        w.writerow([name, ap, bp, "" if og is None else og, ag, conf,
                    "b3_blind" if blind else "contaminated_prior_exposure",
                    outcome(ap, bp, og), outcome(ap, bp, ag)])

(B4 / "tier0_sensitivity.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
