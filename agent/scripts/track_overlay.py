"""YOLO 추적 오버레이 — 대상 선수를 사각형으로 따라가는 검수용 영상을 만든다.

분석 파이프라인 본체가 아니라 **검수 도구**다. 지도자·팀원이 "에이전트가 누구를
보고 있는지"를 눈으로 확인하기 위한 것이라, 본체(RT-DETR)와 별개로 돈다.

    uv run --extra tracking python scripts/track_overlay.py <영상> [-o 출력.mp4]

⚠️ ultralytics는 AGPL-3.0이다. 선택 의존성(`--extra tracking`)으로 분리해 두었고
   서비스 경로에는 넣지 않는다. pyproject.toml의 주석 참고.

대상 선정 규칙
    추적 ID별로 "화면에서 차지한 면적의 합"을 재고 가장 큰 ID를 대상으로 삼는다.
    프레임마다 가장 큰 박스를 고르는 pose.py의 규칙과 달리, 한 번 정한 대상을
    클립 내내 유지한다 — 배경 인물이 잠깐 더 크게 잡혀도 대상이 바뀌지 않는다.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

MODEL = "yolo11n.pt"       # nano — 검수용이라 가장 가벼운 것으로 충분하다
PERSON_CLASS = 0
BOX_COLOR = (80, 220, 100)      # BGR
DIM_COLOR = (150, 150, 150)
TRAIL_COLOR = (60, 180, 255)


def track_people(video: Path, model_name: str, conf: float):
    """프레임별 {track_id: (x1, y1, x2, y2, conf)}와 원본 프레임을 돌려준다."""
    from ultralytics import YOLO

    model = YOLO(model_name)
    per_frame: list[dict[int, tuple[float, float, float, float, float]]] = []
    frames: list[np.ndarray] = []

    # persist=True 여야 프레임 간 ID가 유지된다. stream=True로 프레임을 하나씩
    # 받아 4K 클립 전체를 RAM에 올리지 않는다.
    for result in model.track(
        source=str(video), classes=[PERSON_CLASS], conf=conf,
        persist=True, stream=True, verbose=False,
    ):
        frames.append(result.orig_img.copy())
        boxes = result.boxes
        found: dict[int, tuple[float, float, float, float, float]] = {}
        if boxes is not None and boxes.id is not None:
            for box, tid, score in zip(
                boxes.xyxy.cpu().numpy(),
                boxes.id.cpu().numpy().astype(int),
                boxes.conf.cpu().numpy(),
            ):
                found[int(tid)] = (*box.tolist(), float(score))
        per_frame.append(found)

    if not frames:
        raise ValueError(f"프레임을 읽지 못했습니다: {video}")
    return per_frame, frames


def pick_subject(per_frame: list[dict]) -> int | None:
    """클립 전체에서 면적 합이 가장 큰 추적 ID를 대상 선수로 삼는다."""
    area = defaultdict(float)
    for found in per_frame:
        for tid, (x1, y1, x2, y2, _) in found.items():
            area[tid] += (x2 - x1) * (y2 - y1)
    return max(area, key=area.get) if area else None


def draw(frame, box, color, label, thick=2):
    x1, y1, x2, y2 = (int(v) for v in box[:4])
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thick)
    if not label:
        return
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
    cv2.putText(frame, label, (x1 + 4, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2, cv2.LINE_AA)


def render(video: Path, out_path: Path, model_name: str, conf: float, trail: int):
    per_frame, frames = track_people(video, model_name, conf)
    subject = pick_subject(per_frame)

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(
        str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
    )
    if not writer.isOpened():
        raise RuntimeError(f"출력 파일을 열 수 없습니다: {out_path}")

    centers: list[tuple[int, int]] = []
    seen = 0
    for t, (frame, found) in enumerate(zip(frames, per_frame)):
        # 대상이 아닌 인물은 흐린 박스로만 표시해 구분이 되게 한다.
        for tid, box in found.items():
            if tid != subject:
                draw(frame, box, DIM_COLOR, f"#{tid}", thick=1)

        if subject in found:
            seen += 1
            x1, y1, x2, y2, score = found[subject]
            draw(frame, (x1, y1, x2, y2), BOX_COLOR, f"대상 #{subject} {score:.2f}")
            centers.append((int((x1 + x2) / 2), int((y1 + y2) / 2)))
        else:
            centers.append(None)

        # 최근 이동 궤적 — 추적이 튀는지 눈으로 보이게 한다.
        recent = [c for c in centers[max(0, t - trail):t + 1] if c]
        for a, b in zip(recent, recent[1:]):
            cv2.line(frame, a, b, TRAIL_COLOR, 2, cv2.LINE_AA)

        cv2.putText(frame, f"frame {t}", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2, cv2.LINE_AA)
        writer.write(frame)

    writer.release()
    return {
        "frames": len(frames),
        "subject": subject,
        "subject_seen": seen,
        "track_ids": sorted({tid for f in per_frame for tid in f}),
        "fps": fps,
        "size": (w, h),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="YOLO 추적 오버레이 영상 생성")
    ap.add_argument("video", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--trail", type=int, default=25, help="궤적으로 남길 프레임 수")
    args = ap.parse_args()

    out = args.out or args.video.with_name(args.video.stem + "_tracked.mp4")
    info = render(args.video, out, args.model, args.conf, args.trail)

    print(f"출력: {out}")
    print(f"  {info['size'][0]}x{info['size'][1]} @ {info['fps']:.2f}fps, "
          f"{info['frames']}프레임")
    print(f"  추적 ID: {info['track_ids']}")
    print(f"  대상 #{info['subject']} — {info['subject_seen']}/{info['frames']}프레임 "
          f"({info['subject_seen'] / info['frames']:.0%})")


if __name__ == "__main__":
    main()
