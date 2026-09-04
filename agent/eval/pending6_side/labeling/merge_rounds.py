#!/usr/bin/env python3
"""2차 판독 4회차를 1차와 **같은 모양**의 서식 한 장으로 되붙인다.

    uv run python eval/pending6_side/labeling/merge_rounds.py

## 왜 되붙이는가

수집은 회차로 나눠야 독립 관측이 되지만(`make_rounds.py`), **분석은 1차와 같은
코드로 해야 한다.** 사전 등록(`AFTER_LABELS.md`)과 그 구현(`labeled_stats.py`)은
라벨을 보기 전에 굳힌 것이라 지금 고치면 그 성질을 잃는다. 그래서 모양을
맞춰 주고 **분석 코드는 손대지 않는다.**

산출: `review_packet2/side_form_round2.csv`
      (`clip_id,top_hand,swing_arm,swing_leg,subject_ok,note` — 1차와 동일)

`labeled_stats.py`가 읽는 경로는 `review_packet/side_form.csv`로 고정돼 있으므로,
2차로 계산하려면 그 파일을 **가리키게 바꾸지 말고** 산출물을 복사해 넣거나
경로를 인자로 받도록 그때 정한다. **지금 정하지 않는다** — 1차 12건을 덮어쓸지
나란히 둘지는 결과를 보기 전에 결정할 일이 아니다.

## 🔴 줄을 지우지 않는다

1차에서 답이 없는 27줄을 지웠더니 `subject_ok = n`(타자가 아니다)과 `na`(그
동작이 없다)가 합쳐져 되돌릴 수 없게 됐다(`EXCLUDED.md`). 여기서는 39줄이
전부 살아남고, 빈 칸은 빈 칸으로 남는다. 제외는 **계산할 때** 한다.

## 사전 등록된 진단 — 이 서식이 결함을 고쳤는가

되붙인 뒤 **아래 둘을 반드시 함께 찍는다.** 라벨을 보기 전에 정해 둔다.

    (진단 A) swing_arm 이 both 가 아닌 행에서, top_hand 의 반대쪽인 비율
    (진단 B) 같은 행에서 swing_leg 가 swing_arm 과 같은 비율

1차는 둘 다 **8/8 = 100%** 였다. 2차에서도 100%에 가까우면 그것은 서식 결함이
아니라 **실제 신체 상관**이라는 근거가 된다(회차를 나눠 물어도 같았으므로).
반대로 흩어지면 1차 값은 도출이었다는 뜻이다.

🔴 **어느 쪽이 나오든 이 진단만으로 결론짓지 않는다.** 39건이고 `both`를 빼면
분모가 더 작다. 방향을 볼 수 있을 뿐이다.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUNDS_DIR = HERE / "review_packet2"
OUT = ROUNDS_DIR / "side_form_round2.csv"
DISCLOSURE = ROUNDS_DIR / "seen_before.csv"

# 1차 서식의 칸 순서. **바꾸지 않는다** — labeled_stats.py 가 이 모양을 읽는다.
COLUMNS = ["clip_id", "top_hand", "swing_arm", "swing_leg", "subject_ok", "note"]

# 허용값도 1차와 같다(labeled_stats.VOCAB). 빈 칸은 "못 채웠다"이고 허용된다.
VOCAB = {
    "top_hand": {"L", "R", "unclear", "na"},
    "swing_arm": {"L", "R", "both", "unclear", "na"},
    "swing_leg": {"L", "R", "unclear", "na"},
    "subject_ok": {"y", "n"},
    "seen_before": {"y", "n"},
}

ROUND_FILES = [
    ("round1_subject.csv", ["subject_ok", "seen_before"]),
    ("round2_leg.csv", ["swing_leg"]),
    ("round3_arm.csv", ["swing_arm"]),
    ("round4_top_hand.csv", ["top_hand"]),
]

OPPOSITE = {"L": "R", "R": "L"}


def read_round(name: str, fields: list[str]) -> dict[str, dict[str, str]]:
    path = ROUNDS_DIR / name
    if not path.exists():
        sys.exit(f"회차 파일이 없다: {path}\n  먼저 make_rounds.py 를 돌릴 것")

    out: dict[str, dict[str, str]] = {}
    bad: list[str] = []
    for row in csv.DictReader(open(path, encoding="utf-8")):
        cid = row["clip_id"].strip()
        vals = {}
        for f in fields:
            v = (row.get(f) or "").strip()
            if v and v not in VOCAB[f]:
                bad.append(f"{name}:{cid} {f}={v!r}")
            vals[f] = v
        note = (row.get("note") or "").strip()
        if note:
            # 어느 회차의 메모인지 남긴다 — 합치면 출처를 잃는다.
            vals["_note"] = f"[{name.split('_')[0]}] {note}"
        out[cid] = vals

    if bad:
        sys.exit("🔴 허용되지 않는 값이 있다. 고치고 다시 돌릴 것:\n  "
                 + "\n  ".join(bad))
    return out


def main() -> None:
    rounds = {name: read_round(name, fields) for name, fields in ROUND_FILES}

    # 대상 명단은 회차들의 합집합이다. 어느 회차에서 빠진 클립이 있으면 드러난다.
    ids = sorted({cid for r in rounds.values() for cid in r})
    for name, r in rounds.items():
        missing = [c for c in ids if c not in r]
        if missing:
            print(f"⚠️  {name}에 없는 클립 {len(missing)}건: {', '.join(missing)}")

    merged: list[dict[str, str]] = []
    for cid in ids:
        row = {c: "" for c in COLUMNS}
        row["clip_id"] = cid
        notes = []
        for name, fields in ROUND_FILES:
            vals = rounds[name].get(cid, {})
            for f in fields:
                if f in COLUMNS:
                    row[f] = vals.get(f, "")
            if vals.get("_note"):
                notes.append(vals["_note"])
        row["note"] = " ".join(notes)
        merged.append(row)

    filled = sum(1 for r in merged
                 if any(r[c] for c in ("top_hand", "swing_arm",
                                       "swing_leg", "subject_ok")))
    if not filled:
        sys.exit(
            f"🔴 네 회차가 전부 비어 있다 ({len(merged)}행). 되붙이지 않는다.\n"
            f"   빈 서식을 산출로 남기면 그것이 결과처럼 인용된다\n"
            f"   (labeled_stats.py 가 같은 이유로 멈춘다).\n"
            "   판독 절차: review_packet2/INSTRUCTIONS.md"
        )

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(merged)

    # 고지는 별도 파일이다 — 1차 서식 모양에 없는 칸이라 섞으면 계약이 깨진다.
    seen = rounds["round1_subject.csv"]
    with open(DISCLOSURE, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["clip_id", "seen_before"])
        for cid in ids:
            w.writerow([cid, seen.get(cid, {}).get("seen_before", "")])

    print(f"{OUT.name}: {len(merged)}행 (내용이 있는 행 {filled})")
    print(f"{DISCLOSURE.name}: 본 적 있다고 적힌 클립 "
          f"{sum(1 for cid in ids if seen.get(cid, {}).get('seen_before') == 'y')}건")

    diagnose(merged)


def diagnose(merged: list[dict[str, str]]) -> None:
    """사전 등록된 진단 A·B. 위 docstring 참고."""
    rows = [r for r in merged
            if r["swing_arm"] in ("L", "R") and r["top_hand"] in ("L", "R")]
    print("\n서식 진단 (사전 등록) — 세 칸이 서로 독립인가")
    if not rows:
        print("  swing_arm 과 top_hand 가 둘 다 L/R 인 행이 없다. 진단 불가.")
        return

    a = sum(1 for r in rows if r["swing_arm"] == OPPOSITE[r["top_hand"]])
    print(f"  A. swing_arm 이 top_hand 의 반대쪽: {a}/{len(rows)}"
          f"   (1차는 8/8 이었다)")

    leg = [r for r in rows if r["swing_leg"] in ("L", "R")]
    if leg:
        b = sum(1 for r in leg if r["swing_leg"] == r["swing_arm"])
        print(f"  B. swing_leg 가 swing_arm 과 같음: {b}/{len(leg)}"
              f"   (1차는 8/8 이었다)")

    print("  🔴 이 수만으로 결론짓지 않는다 — 분모가 작고 방향만 보인다.")


if __name__ == "__main__":
    main()
