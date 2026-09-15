"""B-6 산출 두 판을 대 본다 (미결 `ho` 43번 ㉳ 3회차 기준 E).

대조 규칙은 `eval/phaseA/eval_b6/RERUN.md` 의 「재실행 후 대조 절차」 그대로다.
🔴 **키는 `(track, clip_id, comparison_selector)`** 이고 305행이 1:1 이어야 한다.

    uv run python eval/pending43_leak_fix/compare_b6.py <전> <후> [--label E-1]

`<전>`·`<후>` 는 `selector_downstream_comparison.csv` 가 있는 **디렉터리**다
(같은 폴더의 `selector_downstream_rubric_clips.csv` 도 함께 읽는다).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

FILES = ("selector_downstream_comparison.csv", "selector_downstream_rubric_clips.csv")
KEY = ("track", "clip_id", "comparison_selector")

#: 임팩트 정의와 **무관한** 열 — selector 와 포즈에만 의존한다 (RERUN.md).
IMPACT_FREE = (
    "frames", "multi_candidate_frames", "selected_target_difference",
    "selected_target_difference_ratio", "detected_frames",
    "usable_ratio_arm", "usable_ratio_leg",
)

#: 이 회차가 **바꾸기로 한** 열. E-2 는 이 둘을 빼고 전부 같기를 요구한다.
EXPECTED_TO_CHANGE = (
    "follow_through_duration_frames", "delta_follow_through_duration_frames",
)

#: 등급·점수 — 기준 D (2회차의 「누수는 밴드가 아니라 근거로 나간다」 시험).
VERDICT = ("grade", "grade_changed", "score")


def load(folder: Path) -> dict[tuple, dict]:
    rows: dict[tuple, dict] = {}
    for name in FILES:
        path = folder / name
        if not path.exists():
            raise SystemExit(f"없다: {path}")
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                rows[tuple(row[k] for k in KEY)] = row
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    a, b = load(Path(args.before)), load(Path(args.after))
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))

    print(f"## B-6 대조 {args.label}\n")
    print(f"- 행 수: 전 **{len(a)}** · 후 **{len(b)}** (305 예상)")
    print(f"- 키 집합: 전에만 **{len(only_a)}** · 후에만 **{len(only_b)}**")
    if only_a or only_b:
        print("\n🔴 키가 안 맞는다 — RERUN.md N-4(입력 파일 집합)를 먼저 의심한다.")
        for k in (only_a + only_b)[:20]:
            print("  " + str(k))
        print("\n🔴 **아래는 겹치는 키만** 대조한 것이다 — 행 수 판정은 이미 깨졌다.")

    shared = sorted(set(a) & set(b))
    columns = [c for c in a[shared[0]] if c in b[shared[0]]]
    diff: dict[str, list[str]] = {}
    for key in shared:
        for col in columns:
            if a[key][col] != b[key][col]:
                diff.setdefault(col, []).append(
                    f"{'|'.join(key)}: {a[key][col]!r} → {b[key][col]!r}")

    print(f"\n### 열별 불일치 ({len(diff)}열)\n")
    if not diff:
        print("**없다 — 305행 × 전 열 완전 일치.**")
    else:
        print("| 열 | 불일치 행 | 보기 |")
        print("|---|---:|---|")
        for col in sorted(diff, key=lambda c: -len(diff[c])):
            print(f"| `{col}` | {len(diff[col])} | {diff[col][0][:90]} |")

    impact_free_bad = {c: len(v) for c, v in diff.items() if c in IMPACT_FREE}
    verdict_bad = {c: len(v) for c, v in diff.items() if c in VERDICT}
    unexpected = {c: len(v) for c, v in diff.items() if c not in EXPECTED_TO_CHANGE}

    print("\n### 판정에 쓰는 것\n")
    print("| | 내용 | 결과 | |")
    print("|---|---|---|---|")
    print(f"| 행·키 | 305행 1:1 | 전 {len(a)} · 후 {len(b)} · 겹침 {len(shared)} "
          f"| {'✅' if not (only_a or only_b) else '🔴'} |")
    print(f"| 임팩트 무관 6열 | 완전 일치 | 불일치 열 **{len(impact_free_bad)}** "
          f"| {'✅' if not impact_free_bad else '🔴'} |")
    print(f"| D — 등급·점수 | 한 행도 안 바뀜 | 불일치 열 **{len(verdict_bad)}** "
          f"| {'✅' if not verdict_bad else '🔴'} |")
    print(f"| E-2 — 마무리 길이 두 열 말고 | 전부 일치 | 그 밖 불일치 열 "
          f"**{len(unexpected)}** | {'✅' if not unexpected else '🔴'} |")
    if unexpected:
        print("\n🔴 마무리 길이 밖에서 달라진 열:", ", ".join(sorted(unexpected)))


if __name__ == "__main__":
    main()
