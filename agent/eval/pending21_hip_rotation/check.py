#!/usr/bin/env python3
"""사전 등록 기준 A~F로 B-6 재실행 결과를 대조한다 (미결 21번).

    uv run python eval/pending21_hip_rotation/check.py

기준은 `PREREGISTRATION.md`에 코드 변경 **전에** 고정했다. 여기서 고치지 않는다.
조사 스크립트라 `src/`를 건드리지 않는다 — CSV만 읽는다.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
B6 = HERE.parents[1] / "eval" / "phaseA" / "eval_b6" if False else HERE.parent / "phaseA" / "eval_b6"

PAIRS = [
    ("Track 1", HERE / "before_comparison.csv", B6 / "selector_downstream_comparison.csv"),
    ("Track 2", HERE / "before_rubric_clips.csv", B6 / "selector_downstream_rubric_clips.csv"),
]

KEY = ("track", "clip_id", "comparison_selector")

#: A — selector·포즈에만 의존한다. 어긋나면 내 변경이 아니라 환경이 변한 것이다.
COLS_A = ("frames", "multi_candidate_frames", "selected_target_difference",
          "selected_target_difference_ratio", "detected_frames",
          "usable_ratio_arm", "usable_ratio_leg")
COLS_B = ("impact_frame",)
COLS_C = ("hip_rotation_range_deg", "delta_hip_rotation_range_deg")
COLS_E = ("grade", "grade_changed")
COLS_F = ("features_ok", "fail_reason", "rubric", "rubric_status")


def load(p: Path) -> dict[tuple, dict]:
    with open(p, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {tuple(r.get(k, "") for k in KEY): r for r in rows}


def main() -> int:
    bad = 0
    for name, bp, ap in PAIRS:
        print(f"\n{'='*66}\n{name}\n{'='*66}")
        if not ap.exists():
            print(f"  🔴 재실행 산출물이 없다: {ap}")
            bad += 1
            continue
        before, after = load(bp), load(ap)

        # 행 수·키 집합이 먼저 같아야 한다 (RERUN.md 대조 절차)
        if before.keys() != after.keys():
            only_b = list(before.keys() - after.keys())[:3]
            only_a = list(after.keys() - before.keys())[:3]
            print(f"  🔴 키 집합이 다르다 — before {len(before)} · after {len(after)}")
            print(f"     before에만: {only_b}\n     after에만 : {only_a}")
            print("     → N-4(입력 파일 집합)를 먼저 의심할 것")
            bad += 1
            continue
        print(f"  행 {len(before)} · 키 집합 일치 ✅")

        present = set(next(iter(before.values())))

        def diff(cols):
            out = {}
            for k in before:
                for c in cols:
                    if c not in present:
                        continue
                    b, a = before[k].get(c, ""), after[k].get(c, "")
                    if b != a:
                        out.setdefault(c, []).append((k, b, a))
            return out

        # --- A·B·F: 완전 일치여야 한다 ---------------------------------
        for label, cols, why in (
            ("A", COLS_A, "selector·포즈 의존 — 어긋나면 환경 변화(N-1부터)"),
            ("B", COLS_B, "임팩트 정의를 안 건드렸다"),
            ("F", COLS_F, "키가 빠지는 것은 품질 게이트 실패가 아니다"),
        ):
            d = diff(cols)
            if d:
                print(f"  🔴 {label} 불합격 — {why}")
                for c, items in d.items():
                    print(f"     {c}: {len(items)}행 (예: {items[0]})")
                bad += 1
            else:
                print(f"  {label} 합격 ✅ ({why})")

        # --- C: hip_rotation 은 0.0 이던 행에서만 빈칸이 된다 -----------
        zero_keys = {k for k, r in before.items()
                     if r.get("hip_rotation_range_deg", "").strip() in ("0.0", "0.00", "0")}
        c_bad = []
        for k in before:
            b = before[k].get("hip_rotation_range_deg", "")
            a = after[k].get("hip_rotation_range_deg", "")
            if k in zero_keys:
                if a.strip() != "":
                    c_bad.append(("0.0인데 빈칸이 아니다", k, b, a))
            elif b != a:
                c_bad.append(("0.0이 아닌데 바뀌었다", k, b, a))
        if c_bad:
            print(f"  🔴 C 불합격 — {len(c_bad)}건")
            for it in c_bad[:5]:
                print(f"     {it}")
            bad += 1
        else:
            print(f"  C 합격 ✅ (0.0이던 {len(zero_keys)}행만 빈칸이 됐다)")

        # --- D: 나머지 지표는 완전 일치 --------------------------------
        others = [c for c in present
                  if c not in COLS_A + COLS_B + COLS_C + COLS_E + COLS_F + KEY
                  and c != "production_selector" and c != "score"]
        d = diff(others)
        # hip_rotation 이 빠지면 delta_* 도 함께 빈다 — C 에서 이미 본 행만 허용
        d = {c: [x for x in items if x[0] not in zero_keys] for c, items in d.items()}
        d = {c: v for c, v in d.items() if v}
        if d:
            print(f"  🔴 D 불합격 — 0.0이 아니던 행에서 다른 지표가 바뀌었다")
            for c, items in d.items():
                print(f"     {c}: {len(items)}행 (예: {items[0]})")
            bad += 1
        else:
            print("  D 합격 ✅ (나머지 지표는 0.0이던 행 밖에서 그대로다)")

        # --- E: 등급은 0.0이던 클립에서만 --------------------------------
        zero_clips = {k[1] for k in zero_keys}
        e_bad = [(c, k, before[k].get(c), after[k].get(c))
                 for c in COLS_E if c in present
                 for k in before
                 if before[k].get(c) != after[k].get(c) and k[1] not in zero_clips]
        if e_bad:
            print(f"  🔴 E 불합격 — 무관한 클립에서 등급이 바뀌었다: {len(e_bad)}건")
            for it in e_bad[:5]:
                print(f"     {it}")
            bad += 1
        else:
            changed = [k for c in COLS_E if c in present for k in before
                       if before[k].get(c) != after[k].get(c)]
            print(f"  E 합격 ✅ (등급 변동 {len(changed)}건, 전부 0.0이던 클립 안)")

    print(f"\n{'='*66}")
    print("판정:", "✅ 전 항목 합격 — 채택" if bad == 0 else f"🔴 {bad}개 항목 불합격 — 되돌리고 원인부터")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
