"""대상 선수 라벨링 CLI — 117개 대상을 하나씩 묻는다.

    uv run python eval/phaseA/labeling/label_cli.py

라벨러가 답할 것은 하나다: **이 프레임에서 실제 분석 대상인 타자는 몇 번 후보인가?**

selector(baseline·A·B)가 무엇을 골랐는지는 이 화면에 나오지 않는다. 렌더 이미지도
모든 후보를 같은 색으로 그린다 — 정답을 유도하지 않기 위해서다.

입력:
    0..N-1   해당 번호 후보가 타자
    n, none  판별 불가 / 타자가 화면에 없음 / 후보에 타자가 없음 (null)
    s        건너뛰기 (라벨을 남기지 않는다 — 나중에 다시 묻는다)
    b        이전 대상으로
    q        저장하고 종료

입력할 때마다 즉시 저장하므로 중간에 끊겨도 잃지 않는다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from targets import LABELS, RENDERS, enumerate_targets, load_candidates, target_key  # noqa: E402


def load_labels() -> dict:
    if LABELS.exists():
        return json.loads(LABELS.read_text())
    return {
        "version": 1,
        "source": "/mnt/d/supersub-phaseA/",
        "box_index_domain": "candidates/*.npz 프레임별 후보 배열의 인덱스 (RT-DETR person, score>=0.3, 저장 순서)",
        "frames": [],
    }


def save_labels(doc: dict) -> None:
    doc["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tmp = LABELS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(LABELS)          # 원자적 교체 — 쓰다 끊겨도 이전 파일이 남는다


def open_image(path: Path) -> None:
    """WSL/리눅스에서 가능한 뷰어로 띄운다. 실패해도 진행에는 영향이 없다."""
    for cmd in (["wslview", str(path)], ["xdg-open", str(path)]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue


def main() -> None:
    targets = enumerate_targets()
    doc = load_labels()
    done = {target_key(f["clip_id"], f["ratio"]): f for f in doc["frames"]}

    i = 0
    total = len(targets)
    while 0 <= i < total:
        t = targets[i]
        key = target_key(t["clip_id"], t["ratio"])
        per_frame, _, _ = load_candidates(t["clip_id"])
        boxes = per_frame[t["frame"]]
        img = RENDERS / "single" / f"{t['clip_id']}@{t['ratio']:.2f}.jpg"

        labeled = len(done)
        print("\n" + "=" * 62)
        print(f"[{i + 1} / {total}]   라벨 완료 {labeled}/{total}")
        print(f"clip:  {t['clip_id']}")
        print(f"frame: {t['frame']} / {t['n_frames'] - 1}   ratio: {t['ratio']:.0%}")
        print(f"candidates: {len(boxes)}")
        print(f"image: {img}")
        for j, (x1, y1, x2, y2, score) in enumerate(boxes):
            print(f"   [{j}] score {score:.2f}   box ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")
        if not len(boxes):
            print("   (후보 없음 — n 으로 넘긴다)")
        if key in done:
            print(f"  * 기존 라벨: {done[key]['box_index']}")

        if img.exists():
            open_image(img)

        try:
            raw = input("실제 타자 후보 번호 > ").strip().lower()
        except EOFError:
            break

        if raw == "q":
            break
        if raw == "b":
            i = max(0, i - 1)
            continue
        if raw == "s":
            i += 1
            continue
        if raw in ("n", "none", "null"):
            value = None
        else:
            try:
                value = int(raw)
            except ValueError:
                print("  ! 0~N-1 숫자, n(none), s(skip), b(back), q(quit) 중 하나")
                continue
            if not (0 <= value < len(boxes)):
                print(f"  ! 후보 범위는 0~{len(boxes) - 1} 이다")
                continue

        record = {
            "clip_id": t["clip_id"],
            "frame": t["frame"],
            "ratio": t["ratio"],
            "box_index": value,
        }
        if key in done:
            doc["frames"] = [f for f in doc["frames"] if target_key(f["clip_id"], f["ratio"]) != key]
        doc["frames"].append(record)
        done[key] = record
        save_labels(doc)
        i += 1

    save_labels(doc)
    print(f"\n저장: {LABELS}  ({len(doc['frames'])}/{total})")


if __name__ == "__main__":
    main()
