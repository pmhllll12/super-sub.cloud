"""라벨 파일 검증 — 실패하면 exit code 1.

검사 항목 (지시서 10절):
    1. 총 target 수 = 117
    2. clip 수 = 39
    3. clip당 target = 3
    4. ratio가 20/50/80
    5. frame이 해당 clip의 유효 범위
    6. box_index가 해당 frame의 candidate 범위
    7. null 허용
    8. 중복 label 없음
    9. 누락 target 없음
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from targets import LABELS, RATIOS, enumerate_targets, load_candidates, target_key  # noqa: E402

EXPECTED_TARGETS = 117
EXPECTED_CLIPS = 39
EXPECTED_PER_CLIP = 3


def main() -> int:
    problems: list[str] = []

    targets = enumerate_targets()
    by_key = {target_key(t["clip_id"], t["ratio"]): t for t in targets}
    clips = sorted({t["clip_id"] for t in targets})

    # 1~4: 대상 자체의 구조
    if len(targets) != EXPECTED_TARGETS:
        problems.append(f"target 수가 {len(targets)} (기대 {EXPECTED_TARGETS})")
    if len(clips) != EXPECTED_CLIPS:
        problems.append(f"clip 수가 {len(clips)} (기대 {EXPECTED_CLIPS})")
    per_clip = Counter(t["clip_id"] for t in targets)
    bad = {c: n for c, n in per_clip.items() if n != EXPECTED_PER_CLIP}
    if bad:
        problems.append(f"clip당 target이 {EXPECTED_PER_CLIP}이 아닌 것: {bad}")
    bad_ratio = {t["ratio"] for t in targets} - set(RATIOS)
    if bad_ratio:
        problems.append(f"허용되지 않은 ratio: {sorted(bad_ratio)}")

    if not LABELS.exists():
        print(f"라벨 파일이 없다: {LABELS}")
        return 1
    doc = json.loads(LABELS.read_text())
    records = doc.get("frames", [])

    # 8: 중복
    keys = [target_key(r["clip_id"], r["ratio"]) for r in records]
    dupes = {k: n for k, n in Counter(keys).items() if n > 1}
    if dupes:
        problems.append(f"중복 라벨: {dupes}")

    # 알 수 없는 대상
    unknown = [k for k in keys if k not in by_key]
    if unknown:
        problems.append(f"대상 목록에 없는 라벨: {unknown[:5]}")

    invalid = 0
    n_null = 0
    cand_cache: dict[str, list] = {}
    for r in records:
        key = target_key(r["clip_id"], r["ratio"])
        t = by_key.get(key)
        if t is None:
            continue
        # 5: frame 범위 + 대상 프레임과 일치
        if r["frame"] != t["frame"]:
            problems.append(f"{key}: frame {r['frame']}이 대상 {t['frame']}과 다르다")
            invalid += 1
            continue
        if not (0 <= r["frame"] < t["n_frames"]):
            problems.append(f"{key}: frame {r['frame']}이 범위 밖 (0~{t['n_frames'] - 1})")
            invalid += 1
            continue
        # 6~7: box_index 범위, null 허용
        bi = r.get("box_index", "MISSING")
        if bi == "MISSING":
            problems.append(f"{key}: box_index 필드가 없다")
            invalid += 1
            continue
        if bi is None:
            n_null += 1
            continue
        if r["clip_id"] not in cand_cache:
            cand_cache[r["clip_id"]], _, _ = load_candidates(r["clip_id"])
        k = len(cand_cache[r["clip_id"]][r["frame"]])
        if not isinstance(bi, int) or not (0 <= bi < k):
            problems.append(f"{key}: box_index {bi}가 후보 범위 밖 (0~{k - 1})")
            invalid += 1

    # 9: 누락
    missing = [k for k in by_key if k not in set(keys)]

    print("Label validation")
    print("---------------")
    print(f"clips: {len(clips)}")
    print(f"targets: {len(targets)}")
    print(f"labeled: {len(records)}")
    print(f"null: {n_null}")
    print(f"missing: {len(missing)}")
    print(f"invalid: {invalid}")
    print(f"duplicate: {len(dupes)}")

    if missing:
        print(f"\n누락 대상 (앞 10개): {missing[:10]}")
    if problems:
        print("\n문제:")
        for p in problems[:20]:
            print(f"  - {p}")

    ok = not problems and not missing and invalid == 0
    print(f"\nresult: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
