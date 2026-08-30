"""배치 라벨 입력 — TSV를 읽어 labels.json에 기록한다.

label_cli.py가 대화형이라 사람이 앉아 있어야 한다. 렌더 시트를 보고 한 번에
판단한 결과를 옮겨 담을 때 이쪽을 쓴다. 저장 형식·검증 규칙은 CLI와 같다.

TSV 형식 (탭 또는 공백 구분, # 은 주석):
    <clip_id>  <ratio: 20|50|80>  <box_index 또는 n>   [# 메모]

    uv run python set_labels.py my_labels.tsv --labeler "이름" --note "근거"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from targets import LABELS, enumerate_targets, load_candidates, target_key  # noqa: E402

RATIO_OF = {"20": 0.20, "50": 0.50, "80": 0.80}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv", type=Path)
    ap.add_argument("--labeler", required=True, help="누가 라벨했는지 — 라벨 파일에 남는다")
    ap.add_argument("--note", default="", help="라벨 조건·한계 기록")
    args = ap.parse_args()

    targets = {target_key(t["clip_id"], t["ratio"]): t for t in enumerate_targets()}
    doc = (
        json.loads(LABELS.read_text())
        if LABELS.exists()
        else {
            "version": 1,
            "source": "/mnt/d/supersub-phaseA/",
            "box_index_domain": (
                "candidates/*.npz 프레임별 후보 배열의 인덱스 "
                "(RT-DETR person, score>=0.3, 저장 순서)"
            ),
            "frames": [],
        }
    )
    existing = {target_key(r["clip_id"], r["ratio"]): r for r in doc["frames"]}

    cand_cache: dict[str, list] = {}
    errors: list[str] = []
    written = 0

    for lineno, raw in enumerate(args.tsv.read_text().splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            errors.append(f"{lineno}행: 필드가 3개 미만 — {raw!r}")
            continue
        cid, ratio_s, value_s = parts[0], parts[1], parts[2].lower()
        if ratio_s not in RATIO_OF:
            errors.append(f"{lineno}행: ratio는 20/50/80 — {ratio_s!r}")
            continue
        key = target_key(cid, RATIO_OF[ratio_s])
        t = targets.get(key)
        if t is None:
            errors.append(f"{lineno}행: 대상에 없는 clip/ratio — {key}")
            continue

        if value_s in ("n", "none", "null"):
            value = None
        else:
            try:
                value = int(value_s)
            except ValueError:
                errors.append(f"{lineno}행: box_index가 숫자도 n도 아님 — {value_s!r}")
                continue
            if cid not in cand_cache:
                cand_cache[cid], _, _ = load_candidates(cid)
            k = len(cand_cache[cid][t["frame"]])
            if not (0 <= value < k):
                errors.append(f"{lineno}행: {key} box_index {value}가 범위 밖 (0~{k - 1})")
                continue

        existing[key] = {
            "clip_id": cid,
            "frame": t["frame"],
            "ratio": t["ratio"],
            "box_index": value,
        }
        written += 1

    if errors:
        print("입력 오류 — 아무것도 저장하지 않았다:")
        for e in errors[:20]:
            print(f"  - {e}")
        return 1

    doc["frames"] = [existing[k] for k in sorted(existing)]
    doc["labeler"] = args.labeler
    if args.note:
        doc["note"] = args.note
    doc["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    tmp = LABELS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(LABELS)
    print(f"{written}개 기록 · 파일 전체 {len(doc['frames'])}/117 -> {LABELS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
