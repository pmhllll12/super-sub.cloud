"""사람 검수 입력 검증 — 채워진 폼을 읽어 형식·범위를 검사한다.

**검수 결과를 만들어내지 않는다.** 비어 있는 칸은 비어 있는 채로 보고하고
exit 1로 끝낸다. 자동 추론·기본값 채우기 경로는 존재하지 않는다.

    uv run python ingest_review.py            # 상태 확인
    uv run python ingest_review.py --strict   # 33건 전부 채워져야 통과
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

# targets.py 는 **저장소 것**을 쓴다. /mnt/d 에도 사본이 있지만 그쪽은 갱신되지
# 않아 조용히 옛 동작을 한다 (2026-09-02에 실제로 겪었다 — 라벨 재매핑이
# 반영되지 않은 채 B-1/B-2가 돌았다). 데이터는 /mnt/d, 코드는 저장소다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
from targets import enumerate_targets, load_candidates, target_key  # noqa: E402

B3 = Path("/mnt/d/supersub-phaseA/eval_b3")
ALLOWED_TEXT = {"none", "uncertain"}


def check(path: Path, kind: str) -> tuple[int, int, list[str]]:
    rows = list(csv.DictReader(open(path)))
    problems: list[str] = []
    filled = 0
    cache: dict[str, list] = {}
    targets = {target_key(t["clip_id"], t["ratio"]): t for t in enumerate_targets()}

    for i, r in enumerate(rows, 2):
        v = r["human_box_index"].strip().lower()
        if v == "":
            continue
        filled += 1
        if v in ALLOWED_TEXT:
            continue
        if not v.isdigit():
            problems.append(f"{path.name}:{i} human_box_index='{r['human_box_index']}' "
                            f"— 후보 index 또는 none/uncertain 이어야 한다")
            continue
        idx = int(v)
        if kind == "clip":
            cid = r["clip_id"]
            if cid not in cache:
                cache[cid], _, _ = load_candidates(cid)
            n = len(cache[cid][int(r["frame"])])
        else:
            n = int(r["n_candidates"])
        if not (0 <= idx < n):
            problems.append(f"{path.name}:{i} {r['clip_id']}@{r.get('ratio','') or 'f'+r['frame']} "
                            f"index {idx}가 후보 범위 밖 (0~{n-1})")

    keys = [(r["clip_id"], r["ratio"], r["frame"]) for r in rows]
    dup = {k: c for k, c in Counter(keys).items() if c > 1}
    if dup:
        problems.append(f"{path.name} 중복 행: {dup}")

    if kind == "clip":
        for r in rows:
            k = target_key(r["clip_id"], float(r["ratio"]))
            if k not in targets:
                problems.append(f"{path.name} 대상 목록에 없는 항목: {k}")
            elif targets[k]["frame"] != int(r["frame"]):
                problems.append(f"{path.name} {k}: frame {r['frame']} != 대상 {targets[k]['frame']}")

    return len(rows), filled, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="모든 행이 채워져야 통과 (Step 3 진입 조건)")
    args = ap.parse_args()

    total_problems: list[str] = []
    summary = []
    for name, kind in (("review_input.csv", "clip"), ("soccer_review_input.csv", "soccer")):
        p = B3 / name
        if not p.exists():
            total_problems.append(f"{name} 없음")
            continue
        n, filled, probs = check(p, kind)
        total_problems += probs
        summary.append((name, n, filled))

    print("Human review ingest")
    print("-------------------")
    for name, n, filled in summary:
        print(f"  {name:26s} rows {n:3d}   filled {filled:3d}   empty {n - filled:3d}")

    vals = []
    for name, _ in (("review_input.csv", 0), ("soccer_review_input.csv", 0)):
        p = B3 / name
        if p.exists():
            vals += [r["human_box_index"].strip().lower()
                     for r in csv.DictReader(open(p)) if r["human_box_index"].strip()]
    if vals:
        c = Counter("none" if v == "none" else ("uncertain" if v == "uncertain" else "index")
                    for v in vals)
        print(f"  입력 분포: index {c['index']}  none {c['none']}  uncertain {c['uncertain']}")

    if total_problems:
        print(f"\n문제 {len(total_problems)}건:")
        for p in total_problems[:20]:
            print(f"  - {p}")
        return 1

    all_filled = all(filled == n for _, n, filled in summary)
    if args.strict and not all_filled:
        print("\nresult: BLOCKED — 사람 검수 입력이 완료되지 않았다. "
              "Step 3(verified GT 생성)으로 진행할 수 없다.")
        return 1

    print(f"\nresult: {'READY' if all_filled else 'INCOMPLETE (형식은 정상)'}")
    return 0 if all_filled else 1


if __name__ == "__main__":
    raise SystemExit(main())
