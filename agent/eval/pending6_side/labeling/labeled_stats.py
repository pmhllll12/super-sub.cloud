#!/usr/bin/env python3
"""미결 6번 ④ — `AFTER_LABELS.md` 사전 등록 명세를 그대로 실행한다.

**라벨을 보기 전에 썼다 (2026.09.03).** 그것이 요점이다 — 계산 규칙을 데이터에
맞춰 고르지 않았다는 것을 커밋 순서가 증명한다. `AFTER_LABELS.md`가 "구현하지
않음"이라고 적은 것은 *결과를 보고 규칙을 정하지 말라*는 뜻이었고, 규칙이 이미
고정된 지금 그것을 코드로 굳혀 두는 것은 같은 목적에 부합한다.

    uv run python eval/pending6_side/labeling/labeled_stats.py

`review_packet/side_form.csv`가 비어 있으면 **아무것도 계산하지 않고 멈춘다.**
빈 서식으로 0/0을 내면 그 표가 결과처럼 인용된다.

## 명세와 1:1로 대응한다

| 절 | 여기서 |
|---|---|
| 0 | `denominators()` — 분모 두 벌, 제외 사유별 건수 |
| 1 | `accuracy()` — Wilson 95% CI. `both`는 분자·분모 양쪽에서 뺀다 |
| 2 | `by_margin()` — 구간은 **인자가 아니라 상수**다. 아래 `BINS` 참고 |
| 3 | `fps_split()` — 갈린 클립에서만. 결론을 달지 않는다 |
| 4 | `overall_by_fps()` — 차이의 상한을 함께 찍는다 |
| 5 | `both_and_top_hand()` |
| 6 | `POWER` — 표를 그대로 찍는다 |

## 판정 불가를 세 갈래로 나눈다

`README.md`가 정한 구분이다. 분모에서 빼는 방식이 다르다.

    subject_ok = n   클립 통째로 제외 — 스켈레톤이 타자가 아니다.
                     판별의 정확도와 무관하다 (명세 0절)
    na               그 사지에 동작이 없다 — 해당 사지만 제외 (명세 0절)
    unclear          가려서 안 보인다 — 해당 사지만 제외. **na와 따로 센다**
                     (사람이 못 본 것이지 동작이 없는 것이 아니다)
    both             팔에만 있다. 맞고 틀림이 없으므로 분자·분모 양쪽에서
                     빼고 **따로 보고**한다 (명세 1절·5절)
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORM = HERE / "review_packet" / "side_form.csv"
REFERENCE = HERE / "reference_AFTER_LABELING.csv"

# 🔴 **사전 등록된 구간이다. 분포를 보고 옮기지 않는다.**
# 옮기면 그 순간 사후 선택이 되고, 그때 나온 수치는 근거가 아니다.
BINS = (("<5%", 0.0, 0.05), ("5~10%", 0.05, 0.10),
        ("10~20%", 0.10, 0.20), (">=20%", 0.20, math.inf))

# 정확도를 아예 내지 않는 분모. `AFTER_LABELS.md` 6절의 단서다 —
# 한 자릿수에서 Wilson 구간은 ±30%p 수준이라 "쓸 만한가"조차 못 가른다.
MIN_DENOM_FOR_ACCURACY = 10

SIDE_OF = {"L": "left", "R": "right"}
VOCAB = {
    "top_hand": {"L", "R", "unclear", "na"},
    "swing_arm": {"L", "R", "both", "unclear", "na"},
    "swing_leg": {"L", "R", "unclear", "na"},
    "subject_ok": {"y", "n"},
}

POWER = [
    ("정확도가 50%(동전)보다 높은가", "가능", "39건이면 65% 이상에서 유의"),
    ("정확도가 80%인가 90%인가", "불가", "95% CI 폭이 ±13%p 안팎"),
    ("얇은 마진이 더 틀린다", "불가", "구간당 10건 안팎"),
    ("15fps와 30fps 중 어느 쪽이 나은가", "불가", "갈린 것이 1·6건"),
    ("arm 판별이 이 종목에서 정의되는가", "가능", "both 비율은 세면 된다"),
    ("\"팔 종목에서 약하다\"가 맞는가", "불가", "근거 두 클립은 한 손 동작이다"),
    ("스켈레톤이 타자에게 붙었는가", "가능", "subject_ok가 39건 전부에 답한다"),
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """이항 비율의 Wilson 95% 구간.

    정규근사(Wald)를 쓰지 않는 이유는 n이 작고 비율이 0·1에 붙을 수 있어서다 —
    Wald는 그 구간에서 [0,1]을 넘어서고 폭도 잘못 잡는다.
    """
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, center - half), min(1.0, center + half))


def load() -> tuple[list[dict], dict[str, dict]]:
    if not FORM.exists():
        sys.exit(f"서식이 없다: {FORM}")
    labels = list(csv.DictReader(open(FORM, encoding="utf-8")))

    filled = [r for r in labels
              if any(r[c].strip() for c in ("top_hand", "swing_arm",
                                            "swing_leg", "subject_ok"))]
    if not filled:
        sys.exit(
            f"🔴 서식이 비어 있다 ({len(labels)}행 전부). 계산하지 않는다.\n"
            f"   {FORM}\n"
            "   빈 서식으로 0/0을 내면 그 표가 결과처럼 인용된다.\n"
            "   판독 절차: review_packet/INSTRUCTIONS.md"
        )
    if len(filled) < len(labels):
        done = {r["clip_id"] for r in filled}
        missing = [r["clip_id"] for r in labels if r["clip_id"] not in done]
        print(f"⚠️  {len(missing)}행이 비어 있다: {', '.join(missing)}")
        print("   부분 집계는 낼 수 있으나 분모가 달라진다. 그대로 진행한다.\n")

    bad = []
    for r in labels:
        for col, allowed in VOCAB.items():
            v = r[col].strip()
            if v and v not in allowed:
                bad.append(f"{r['clip_id']}.{col} = {v!r}")
    if bad:
        sys.exit("🔴 알 수 없는 라벨 값:\n  " + "\n  ".join(bad)
                 + "\n허용: " + str(VOCAB))

    ref = {r["clip_id"]: r
           for r in csv.DictReader(open(REFERENCE, encoding="utf-8"))}
    unknown = [r["clip_id"] for r in labels if r["clip_id"] not in ref]
    if unknown:
        sys.exit(f"🔴 대조표에 없는 클립: {unknown}")
    return labels, ref


def denominators(labels: list[dict], ref: dict[str, dict]) -> tuple[list[dict], dict]:
    """명세 0절 — 분모 두 벌과 제외 사유별 건수.

    **전체 분모는 서식이 아니라 대조표에서 온다.** 서식에는 판독된 것만 남고
    (판독자가 "타자가 아니거나 스윙이 아니다"로 뺀 27건은 행 자체가 없다),
    그러면 39라는 수가 파일에서 사라진다. 명세 0절이 요구하는 두 벌 중 한 벌이
    없어지는 것이라 대조표(39행)를 전체 명단으로 쓴다 — 사유는 `EXCLUDED.md`.
    """
    total = len(ref)
    pre = total - len(labels)          # 판독 단계에서 행이 빠진 것
    excluded = [r for r in labels if r["subject_ok"].strip() == "n"]
    kept = [r for r in labels if r["subject_ok"].strip() != "n"]

    print("=" * 66)
    print("A. 유효 분모 (명세 0절)")
    print("=" * 66)
    print(f"  전체 (대조표 기준)            {total}건")
    print(f"  판독 단계 제외                {pre}건  "
          f"(타자 아님 또는 스윙 아님 — EXCLUDED.md)")
    print(f"  → 서식에 남은 것              {len(labels)}건")
    print(f"  subject_ok = n (제외)         {len(excluded)}건"
          + (f"  {[r['clip_id'] for r in excluded]}" if excluded else ""))
    print(f"  → 클립 단위 유효 분모         {len(kept)}건")
    print()
    stats = {}
    for limb, col in (("arm", "swing_arm"), ("leg", "swing_leg")):
        c = {"L": 0, "R": 0, "both": 0, "unclear": 0, "na": 0, "": 0}
        for r in kept:
            c[r[col].strip()] += 1
        usable = c["L"] + c["R"]
        stats[limb] = {"counts": c, "usable": usable}
        print(f"  [{limb}] L {c['L']} · R {c['R']} · both {c['both']} · "
              f"unclear {c['unclear']} · na {c['na']} · 미기입 {c['']}")
        print(f"        → 정확도 분모 {usable}건 "
              f"(both·unclear·na 를 전부 뺀 값)")
    print()
    return kept, stats


def _pairs(kept, ref, limb, col, fps="30"):
    """(라벨 쪽, 자동 쪽, 대조표 행) — L/R 라벨만. both·unclear·na 는 안 나온다."""
    out = []
    for r in kept:
        v = r[col].strip()
        if v not in SIDE_OF:
            continue
        row = ref[r["clip_id"]]
        auto = row[f"auto_{limb}_{fps}"].strip()
        if not auto:
            continue
        out.append((SIDE_OF[v], auto, row))
    return out


def _acc_line(tag: str, k: int, n: int) -> None:
    if n == 0:
        print(f"  {tag}: 분모 0 — 낼 수 없다")
        return
    if n < MIN_DENOM_FOR_ACCURACY:
        print(f"  {tag}: 분모 {n}건. 🔴 **정확도를 내지 않는다** — "
              f"한 자릿수라 Wilson 구간이 ±30%p 수준이다 (명세 6절). "
              f"맞은 수만 적는다: {k}/{n}")
        return
    lo, hi = wilson(k, n)
    print(f"  {tag}: {k}/{n} = {k/n:.1%}  95% CI [{lo:.1%}, {hi:.1%}]")


def accuracy(kept, ref, stats) -> None:
    print("=" * 66)
    print("B-1. 현재 판별 정확도 (명세 1절)")
    print("=" * 66)
    for limb, col in (("arm", "swing_arm"), ("leg", "swing_leg")):
        p = _pairs(kept, ref, limb, col)
        k = sum(1 for lab, auto, _ in p if lab == auto)
        _acc_line(f"[{limb}] auto_{limb}_30 대 라벨", k, len(p))
        c = stats[limb]["counts"]
        if limb == "arm":
            print(f"        both {c['both']}건은 분자·분모 양쪽에서 뺐다 "
                  f"(맞고 틀림이 없다). 5절에서 따로 본다")
        print(f"        unclear {c['unclear']}건(가림) · na {c['na']}건(동작 없음) 제외")
    print()


def by_margin(kept, ref) -> None:
    print("=" * 66)
    print("B-2. 마진 구간별 (명세 2절) — 구간은 사전 등록값, 추세 검정 없음")
    print("=" * 66)
    for limb, col in (("arm", "swing_arm"), ("leg", "swing_leg")):
        p = _pairs(kept, ref, limb, col)
        print(f"  [{limb}]  {'구간':<9}{'맞음':>6}{'분모':>6}   정확도")
        for name, lo, hi in BINS:
            sub = [(l, a) for l, a, row in p
                   if lo <= float(row[f"margin_{limb}_30"]) < hi]
            k = sum(1 for l, a in sub if l == a)
            acc = f"{k/len(sub):.0%}" if sub else "—"
            print(f"          {name:<9}{k:>6}{len(sub):>6}   {acc}")
        print("          (구간당 10건 안팎이라 검정력이 없다. 표까지가 전부다)")
    print()


def fps_split(kept, ref) -> None:
    print("=" * 66)
    print("B-3. 15fps vs 30fps (명세 3절) — 갈린 클립에서만, 결론 없음")
    print("=" * 66)
    for limb, col in (("arm", "swing_arm"), ("leg", "swing_leg")):
        rows = [(lab, row) for lab, _, row in _pairs(kept, ref, limb, col)
                if row[f"flips_{limb}_15v30"] == "1"]
        w30 = sum(1 for lab, row in rows if lab == row[f"auto_{limb}_30"])
        w15 = sum(1 for lab, row in rows if lab == row[f"auto_{limb}_15"])
        print(f"  [{limb}] 갈린 것 중 라벨 있는 것 {len(rows)}건 — "
              f"30fps가 맞은 수 {w30} · 15fps가 맞은 수 {w15}")
    print("  🔴 이 수로 어느 동작점이 낫다고 말하지 않는다. 1건과 6건이다.")
    print("     클립이 독립도 아니고 사전 가설도 없었다 (명세 3절).")
    print()


def overall_by_fps(kept, ref) -> None:
    print("=" * 66)
    print("B-4. 두 동작점 전체 정확도 (명세 4절)")
    print("=" * 66)
    n_dist = sum(1 for r in ref.values() if r["fps15_distinct"] == "1")
    for limb, col in (("arm", "swing_arm"), ("leg", "swing_leg")):
        p = _pairs(kept, ref, limb, col)
        p15 = [(l, row) for l, _, row in p if row[f"auto_{limb}_15"].strip()]
        k30 = sum(1 for l, a, _ in p if l == a)
        k15 = sum(1 for l, row in p15 if l == row[f"auto_{limb}_15"])
        _acc_line(f"[{limb}] target 30", k30, len(p))
        _acc_line(f"[{limb}] target 15", k15, len(p15))
        flips = sum(1 for r in ref.values() if r[f"flips_{limb}_15v30"] == "1")
        print(f"        🔴 두 값의 차이는 갈린 {flips}건 안에 갇혀 있다 "
              f"— 최대 {flips}/{n_dist} = {flips/n_dist:.1%}")
    print()


def both_and_top_hand(kept, ref, stats) -> None:
    print("=" * 66)
    print("B-5. both 와 top_hand (명세 5절)")
    print("=" * 66)
    c = stats["arm"]["counts"]
    decided = c["L"] + c["R"] + c["both"]
    if decided:
        print(f"  swing_arm = both : {c['both']}/{decided} "
              f"({c['both']/decided:.0%} — L·R·both 중에서)")
    if c["both"] > c["L"] + c["R"]:
        print("  🔴 **both가 다수다.** 그러면 물음이 바뀐다 — "
              "\"판별이 부정확한가\"가 아니라")
        print("     \"야구 타격에 arm 스윙 측이라는 개념이 필요한가\"다 (명세 5절).")
    print()
    # top_hand 대 자동 판별 — 정답 판정이 아니라 **일치율**이다.
    # identify_limb 은 top_hand 를 고르겠다고 주장한 적이 없다. 겹치는지만 센다.
    p = [(SIDE_OF[r["top_hand"].strip()], ref[r["clip_id"]]["auto_arm_30"])
         for r in kept if r["top_hand"].strip() in SIDE_OF]
    k = sum(1 for a, b in p if a == b)
    if p:
        print(f"  top_hand 와 auto_arm_30 이 같은 클립: {k}/{len(p)} "
              f"({k/len(p):.0%})")
        print("  이것은 정확도가 아니다 — identify_limb 은 top_hand 를 고르겠다고")
        print("  주장한 적이 없다. 겹치는 정도만 센다 (명세 5절).")
    else:
        print("  top_hand 라벨이 없다.")
    print()


def subject_ok_report(labels, ref) -> None:
    print("=" * 66)
    print("C. subject_ok — 미결 8번(selector)으로 넘길 값")
    print("=" * 66)
    n = sum(1 for r in labels if r["subject_ok"].strip() == "n")
    y = sum(1 for r in labels if r["subject_ok"].strip() == "y")
    print(f"  y {y} · n {n} · 서식에 없음 {len(ref) - len(labels)}")
    print("  🔴 **39건 전수의 답이 아니다.** 판독 단계에서 빠진 클립은 y/n 이")
    print("     매겨지지 않았고, 그중에 selector 가 틀린 것이 섞여 있을 수 있다")
    print("     (O2GSaYqH8JY 가 실제로 그 경우다 — EXCLUDED.md).")
    if n:
        print(f"  n: {[r['clip_id'] for r in labels if r['subject_ok'].strip() == 'n']}")
    print("  🔴 selector 실패와 **검출 실패**는 다르다 — 후보가 1개뿐이었던")
    print("     프레임에서는 고를 것이 없었다 (O2GSaYqH8JY 선례). 이 라벨만으로")
    print("     selector 를 탓할 수 없고, candidate_count 를 함께 봐야 한다.")
    print()


def power() -> None:
    print("=" * 66)
    print("D. 검정력 — 39건으로 말할 수 없는 것 (명세 6절)")
    print("=" * 66)
    for q, verdict, why in POWER:
        print(f"  {verdict:<4} {q}")
        print(f"       {why}")
    print()
    print("  39건이 답하는 것은 \"쓸 만한가/못 쓰는가\"이지 \"얼마나 좋은가\"가 아니다.")
    print()
    # 표는 사전 등록 문안 그대로 찍는다(고치지 않는다). 다만 마지막 줄의 전제가
    # 실제 라벨과 어긋나므로 각주를 단다 — 표를 고치면 등록의 뜻이 없어진다.
    print("  ※ 표의 마지막 줄은 39건 전수에 subject_ok 가 매겨진다는 전제로")
    print("    등록됐다. 실제 판독은 12건에만 매겨졌으므로 그 줄은 지금")
    print("    성립하지 않는다 (C절 참고). 등록 문안이라 표는 고치지 않는다.")
    print()


def main() -> int:
    labels, ref = load()
    kept, stats = denominators(labels, ref)
    accuracy(kept, ref, stats)
    by_margin(kept, ref)
    fps_split(kept, ref)
    overall_by_fps(kept, ref)
    both_and_top_hand(kept, ref, stats)
    subject_ok_report(labels, ref)
    power()
    print("명세: AFTER_LABELS.md · 라벨을 보고 이 스크립트를 고치지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
