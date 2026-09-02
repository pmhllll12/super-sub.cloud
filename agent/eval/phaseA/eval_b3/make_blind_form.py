"""블라인드 검수 입력 폼 생성 — selector 결과와 GT를 일절 담지 않는다.

B-2의 review_cases.csv는 gt_box_index·baseline_box_index·a_box_index·b_box_index·
*_correct·continuity·reason 을 갖고 있어 검수자에게 답을 흘린다. 그 파일은
**수정하지 않고** 여기서 필요한 열만 뽑아 새 폼을 만든다.

검수자가 보는 것: clip_id / ratio / frame / 후보 수 / 렌더 이미지 경로.
검수자가 채우는 것: human_box_index / human_note.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# targets.py 는 **저장소 것**을 쓴다. /mnt/d 에도 사본이 있지만 그쪽은 갱신되지
# 않아 조용히 옛 동작을 한다 (2026-09-02에 실제로 겪었다 — 라벨 재매핑이
# 반영되지 않은 채 B-1/B-2가 돌았다). 데이터는 /mnt/d, 코드는 저장소다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labeling"))
from targets import load_candidates  # noqa: E402

B2 = Path("/mnt/d/supersub-phaseA/eval_b2")
B3 = Path("/mnt/d/supersub-phaseA/eval_b3")
B3.mkdir(exist_ok=True)

FIELDS = ["clip_id", "ratio", "frame", "n_candidates", "image",
          "human_box_index", "human_note"]


def main() -> None:
    src = list(csv.DictReader(open(B2 / "review_cases.csv")))
    rows = []
    for r in sorted(src, key=lambda x: (x["clip_id"], x["ratio"])):
        rows.append({
            "clip_id": r["clip_id"],
            "ratio": r["ratio"],
            "frame": r["frame"],
            "n_candidates": r["candidate_count"],
            "image": f"eval_b2/review_cases/{r['clip_id']}@{r['ratio']}.jpg",
            "human_box_index": "",
            "human_note": "",
        })
    with open(B3 / "review_input.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"review_input.csv: {len(rows)}건 (블라인드)")

    # 축구 5프레임 — 후보 수는 렌더와 같은 조건(score>=0.5)으로 다시 센다
    diffs = list(csv.DictReader(open(B2 / "other_sports_diffs.csv")))
    seen, srows = set(), []
    for d in diffs:
        k = (d["video"], int(d["frame"]))
        if k in seen:
            continue
        seen.add(k)
        srows.append({
            "clip_id": d["video"],
            "ratio": "",
            "frame": d["frame"],
            "n_candidates": d["n_candidates"],
            "image": f"eval_b2/review_cases/SOCCER_{d['video'].replace('.avi','')}@f{int(d['frame']):03d}.jpg",
            "human_box_index": "",
            "human_note": "",
        })
    srows.sort(key=lambda x: int(x["frame"]))
    with open(B3 / "soccer_review_input.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(srows)
    print(f"soccer_review_input.csv: {len(srows)}건 (블라인드)")

    # 폼에 정답이 새어 들어가지 않았는지 자체 검사
    leak = {"gt", "baseline", "a_box", "b_box", "correct", "continuity", "reason",
            "pose_quality", "centrality", "size"}
    for name in ("review_input.csv", "soccer_review_input.csv"):
        cols = set(next(csv.reader(open(B3 / name))))
        bad = [c for c in cols if any(t in c.lower() for t in leak)]
        print(f"  {name} 누출 의심 컬럼: {bad or '없음'}")


if __name__ == "__main__":
    main()
