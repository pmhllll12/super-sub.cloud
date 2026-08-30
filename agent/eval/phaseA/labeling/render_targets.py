"""라벨링용 렌더 — 후보를 전부 **같은 방식으로** 그린다.

편향 방지가 이 스크립트의 유일한 설계 제약이다. baseline·A·B가 무엇을 골랐는지,
어느 박스가 최대인지·최중앙인지 **표시하지 않는다.** 후보를 구분하는 정보는
index와 detection score뿐이며, 색·굵기는 전부 동일하다.

(Phase A의 cand_*.jpg는 최대=빨강·최중앙=초록으로 칠해져 있어 라벨링에 쓸 수 없다.
 그 파일은 대상 프레임과도 대응하지 않는다 — 여기서 새로 만든다.)

출력:
    renders/<clip_id>.jpg                 클립당 3개 대상 프레임을 세로로 이어 붙인 시트
    renders/single/<clip_id>@<ratio>.jpg  대상 하나짜리 이미지 (CLI가 띄운다)
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")

from targets import (  # noqa: E402
    RATIOS,
    RENDERS,
    ROOT,
    clip_ids,
    enumerate_targets,
    frame_at,
    load_candidates,
)

# 후보 표시 — **전부 같은 색·같은 굵기.** 구분은 번호로만 한다.
BOX_COLOR = (255, 200, 0)   # BGR: 하늘색
BOX_THICK = 2
MAX_WIDTH = 1100
# 저해상도 원본은 **키운다.** 578x360짜리 방송 클립에 후보가 23개 붙으면 번호표가
# 서로 겹쳐 읽을 수 없다 — 라벨러가 후보를 구분하지 못하면 라벨 자체가 못 나온다.
MIN_WIDTH = 1100


def sampled_frames(clip_path: Path) -> list[np.ndarray]:
    """Phase A candidates.py와 **동일한 샘플링**으로 원본 프레임을 얻는다.

    production pose.read_frames를 그대로 import한다 — 여기서 규칙을 다시 쓰면
    간격이 어긋나 후보 배열과 프레임이 대응하지 않는다. 읽기만 하고 고치지 않는다.
    """
    from supersub_agent.pose import read_frames

    frames, _, _ = read_frames(str(clip_path), target_fps=15)
    return frames


def draw_candidates(frame: np.ndarray, boxes: np.ndarray, wh: tuple[int, int]) -> np.ndarray:
    """후보 박스와 번호를 그린다. 어떤 후보도 강조하지 않는다."""
    img = frame.copy()
    h0, w0 = img.shape[:2]
    if w0 > MAX_WIDTH:
        img = cv2.resize(img, (MAX_WIDTH, int(h0 * MAX_WIDTH / w0)), interpolation=cv2.INTER_AREA)
    elif w0 < MIN_WIDTH:
        img = cv2.resize(img, (MIN_WIDTH, int(h0 * MIN_WIDTH / w0)), interpolation=cv2.INTER_CUBIC)
    scale = img.shape[1] / wh[0]

    for i, (x1, y1, x2, y2, score) in enumerate(boxes):
        p1 = (int(x1 * scale), int(y1 * scale))
        p2 = (int(x2 * scale), int(y2 * scale))
        cv2.rectangle(img, p1, p2, BOX_COLOR, BOX_THICK, cv2.LINE_AA)

        label = f"{i}  {score:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        # 번호표는 박스 좌상단 바깥에 붙인다. 화면 위로 넘치면 안쪽으로 내린다.
        ty = p1[1] - 4 if p1[1] - th - 8 >= 0 else p1[1] + th + 6
        bx1, by1 = p1[0], ty - th - 4
        bx2, by2 = p1[0] + tw + 8, ty + 4
        cv2.rectangle(img, (bx1, by1), (bx2, by2), (0, 0, 0), -1)
        cv2.rectangle(img, (bx1, by1), (bx2, by2), BOX_COLOR, 1)
        cv2.putText(img, label, (p1[0] + 4, ty), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def header(width: int, text: str) -> np.ndarray:
    bar = np.zeros((30, width, 3), np.uint8)
    cv2.putText(bar, text, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA)
    return bar


def main() -> None:
    RENDERS.mkdir(parents=True, exist_ok=True)
    single = RENDERS / "single"
    single.mkdir(exist_ok=True)

    by_clip: dict[str, list[dict]] = {}
    for t in enumerate_targets():
        by_clip.setdefault(t["clip_id"], []).append(t)

    for idx, cid in enumerate(clip_ids(), 1):
        sheet_path = RENDERS / f"{cid}.jpg"
        if sheet_path.exists():
            print(f"[{idx}/39] skip {cid}", flush=True)
            continue

        per_frame, wh, _ = load_candidates(cid)
        frames = sampled_frames(ROOT / "clips" / f"{cid}.mp4")
        if len(frames) != len(per_frame):
            raise RuntimeError(
                f"{cid}: 디코딩 프레임 {len(frames)}가 후보 캐시 {len(per_frame)}와 다르다"
            )

        tiles = []
        for t in by_clip[cid]:
            f, boxes = t["frame"], per_frame[t["frame"]]
            img = draw_candidates(frames[f], boxes, wh)
            hdr = header(
                img.shape[1],
                f"{cid}   frame {f} / {t['n_frames'] - 1}   ratio {t['ratio']:.0%}"
                f"   candidates {len(boxes)}",
            )
            tile = np.vstack([hdr, img])
            tiles.append(tile)
            cv2.imwrite(str(single / f"{cid}@{t['ratio']:.2f}.jpg"), tile,
                        [cv2.IMWRITE_JPEG_QUALITY, 88])

        w = max(x.shape[1] for x in tiles)
        padded = [
            np.hstack([x, np.zeros((x.shape[0], w - x.shape[1], 3), np.uint8)])
            if x.shape[1] < w else x
            for x in tiles
        ]
        cv2.imwrite(str(sheet_path), np.vstack(padded), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"[{idx}/39] {cid}  frames={[t['frame'] for t in by_clip[cid]]}"
              f"  cands={[t['n_candidates'] for t in by_clip[cid]]}", flush=True)

    print(f"RENDER DONE -> {RENDERS}", flush=True)


if __name__ == "__main__":
    main()
