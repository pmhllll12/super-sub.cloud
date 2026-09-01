"""라벨링 완료 후 통계 (지시서 11절).

**selector 성능은 계산하지 않는다.** wrong-person rate 비교는 다음 단계다.
여기서 내는 것은 라벨 자체의 분포뿐이다.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from targets import LABELS, enumerate_targets, target_key  # noqa: E402


def main() -> None:
    targets = enumerate_targets()
    by_key = {target_key(t["clip_id"], t["ratio"]): t for t in targets}
    doc = json.loads(LABELS.read_text()) if LABELS.exists() else {"frames": []}
    records = {target_key(r["clip_id"], r["ratio"]): r for r in doc["frames"]}

    total = len(targets)
    labeled = len(records)
    nulls = sum(1 for r in records.values() if r["box_index"] is None)

    print("=== 라벨 진행 ===")
    print(f"  전체 대상        {total}")
    print(f"  라벨 완료        {labeled}")
    print(f"  null            {nulls}")
    print(f"  미완료           {total - labeled}")

    print("\n=== 대상별 후보 수 ===")
    c0 = sum(1 for t in targets if t["n_candidates"] == 0)
    c1 = sum(1 for t in targets if t["n_candidates"] == 1)
    c2 = sum(1 for t in targets if t["n_candidates"] >= 2)
    print(f"  후보 0개         {c0}")
    print(f"  후보 1개         {c1}")
    print(f"  후보 2개 이상     {c2}")
    print(f"  후보 수 최대      {max(t['n_candidates'] for t in targets)}")

    print("\n=== clip별 완료 여부 ===")
    clips = sorted({t["clip_id"] for t in targets})
    incomplete = []
    for cid in clips:
        keys = [target_key(cid, r) for r in (0.20, 0.50, 0.80)]
        n = sum(1 for k in keys if k in records)
        if n != 3:
            incomplete.append((cid, n))
    print(f"  3개 모두 완료한 clip  {len(clips) - len(incomplete)}/{len(clips)}")
    if incomplete:
        print(f"  미완료: {incomplete}")

    print("\n=== clip별 후보 수 (대상 3프레임) ===")
    for cid in clips:
        ts = [t for t in targets if t["clip_id"] == cid]
        got = [records.get(target_key(cid, t["ratio"])) for t in ts]
        marks = "".join(
            "-" if g is None else ("n" if g["box_index"] is None else str(g["box_index"]))
            for g in got
        )
        print(f"  {cid:14s} cands={[t['n_candidates'] for t in ts]}  labels={marks}")

    print("\n=== 선택된 box_index 분포 ===")
    idx = Counter(r["box_index"] for r in records.values() if r["box_index"] is not None)
    for k in sorted(idx):
        print(f"  index {k}: {idx[k]}")
    print("  (이 분포는 후보 저장 순서에 대한 것이며, selector 성능을 뜻하지 않는다.)")

    # 후보가 여럿인 대상에서 null이 난 비율 — 라벨 난이도의 지표다.
    hard = [k for k, r in records.items()
            if r["box_index"] is None and by_key[k]["n_candidates"] >= 2]
    print(f"\n  후보 2개 이상인데 판별 불가로 null: {len(hard)}")
    for k in hard:
        print(f"    {k}  (candidates {by_key[k]['n_candidates']})")


if __name__ == "__main__":
    main()
