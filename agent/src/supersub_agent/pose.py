"""영상 → COCO-17 키포인트 시계열.

필수 투입자원 목록에 MediaPipe가 없으므로 **OpenCV + Transformers**로 구성한다.
  - OpenCV: 디코딩, 프레임 샘플링
  - Transformers RT-DETR: 사람 검출 (ViTPose가 top-down 방식이라 필요)
  - Transformers ViTPose: 포즈 추정

판정 모델(EXAONE)과 동시에 GPU에 올리지 않는다. 8GB에서는 순차 실행한다 —
포즈 추출을 끝내고 모델을 해제한 뒤 판정 단계로 넘어간다.
"""

from __future__ import annotations

import gc
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

PERSON_DETECTOR = "PekingU/rtdetr_r50vd_coco_o365"
POSE_MODEL = "usyd-community/vitpose-base-simple"
COCO_PERSON_LABEL = 0


@dataclass
class PoseResult:
    keypoints: np.ndarray      # (T, 17, 3) — x, y, confidence
    frames: list[np.ndarray]   # 샘플링된 원본 프레임 (오버레이용)
    source_fps: float
    sampled_fps: float         # 실효 샘플링 fps (목표값이 아니라 src_fps / step)

    def frame_to_seconds(self, frame: int) -> float:
        """샘플링된 프레임 인덱스를 원본 영상의 시각(초)으로 환산한다."""
        return frame / self.sampled_fps


def read_frames(
    video_path: str | Path, target_fps: int = 15, max_frames: int = 300
) -> tuple[list[np.ndarray], float, float]:
    """OpenCV로 디코딩하고 target_fps에 가장 가까운 정수 간격으로 다운샘플링한다.

    반환값은 (프레임, 원본 fps, **실효** 샘플링 fps)다.

    간격이 정수라 target_fps를 그대로 달성하지 못한다 — 25fps 영상에 target 15를
    주면 step=round(1.67)=2, 즉 실효 12.5fps다. 목표값을 실효값인 양 기록하면
    프레임 인덱스를 시각으로 환산할 때 20% 어긋난다.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(src_fps / target_fps))

    frames: list[np.ndarray] = []
    idx = 0
    while len(frames) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            frames.append(frame)
        idx += 1
    cap.release()

    if not frames:
        raise ValueError(f"프레임을 읽지 못했습니다: {video_path}")
    return frames, src_fps, src_fps / step


def _largest_person_box(detections, threshold: float = 0.5):
    """가장 큰 사람 박스를 대상 선수로 삼는다.

    다중 인원 영상에서 화면 중앙의 큰 피사체가 촬영 대상이라는 가정.
    관중이나 배경 인물이 더 크게 잡히는 구도라면 이 규칙은 재검토해야 한다.
    """
    best, best_area = None, 0.0
    for score, label, box in zip(
        detections["scores"], detections["labels"], detections["boxes"]
    ):
        if int(label) != COCO_PERSON_LABEL or float(score) < threshold:
            continue
        x1, y1, x2, y2 = [float(v) for v in box]
        area = (x2 - x1) * (y2 - y1)
        if area > best_area:
            best, best_area = (x1, y1, x2 - x1, y2 - y1), area  # COCO xywh
    return best


def extract_keypoints(
    video_path: str | Path, target_fps: int = 15, device: str | None = None
) -> PoseResult:
    """영상에서 대상 선수의 키포인트 시계열을 추출한다."""
    import torch
    from transformers import (
        AutoProcessor,
        RTDetrForObjectDetection,
        VitPoseForPoseEstimation,
    )

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    frames, src_fps, sampled_fps = read_frames(video_path, target_fps)

    det_processor = AutoProcessor.from_pretrained(PERSON_DETECTOR)
    detector = RTDetrForObjectDetection.from_pretrained(PERSON_DETECTOR).to(device).eval()
    pose_processor = AutoProcessor.from_pretrained(POSE_MODEL)
    pose_model = VitPoseForPoseEstimation.from_pretrained(POSE_MODEL).to(device).eval()

    all_kps: list[np.ndarray] = []
    kept_frames: list[np.ndarray] = []

    try:
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            det_inputs = det_processor(images=rgb, return_tensors="pt").to(device)
            with torch.inference_mode():
                det_out = detector(**det_inputs)
            detections = det_processor.post_process_object_detection(
                det_out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3
            )[0]

            box = _largest_person_box(detections)
            if box is None:
                # 사람이 검출되지 않은 프레임은 신뢰도 0으로 채운다.
                all_kps.append(np.zeros((17, 3)))
                kept_frames.append(frame)
                continue

            pose_inputs = pose_processor(
                rgb, boxes=[[list(box)]], return_tensors="pt"
            ).to(device)
            with torch.inference_mode():
                pose_out = pose_model(**pose_inputs)
            results = pose_processor.post_process_pose_estimation(
                pose_out, boxes=[[list(box)]]
            )[0][0]

            kps = np.concatenate(
                [
                    np.asarray(results["keypoints"], dtype=np.float64),
                    np.asarray(results["scores"], dtype=np.float64).reshape(-1, 1),
                ],
                axis=1,
            )
            all_kps.append(kps)
            kept_frames.append(frame)
    finally:
        # 판정 모델을 올릴 VRAM을 비운다.
        del detector, pose_model
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    return PoseResult(
        keypoints=np.stack(all_kps),
        frames=kept_frames,
        source_fps=src_fps,
        sampled_fps=sampled_fps,
    )


# COCO-17 골격 연결 — 오버레이 시각화용
SKELETON = [
    (5, 7), (7, 9), (6, 8), (8, 10),        # 팔
    (5, 6), (5, 11), (6, 12), (11, 12),     # 몸통
    (11, 13), (13, 15), (12, 14), (14, 16),  # 다리
]


def draw_overlay(frame: np.ndarray, kps: np.ndarray, min_conf: float = 0.3) -> np.ndarray:
    """스켈레톤을 그린 프레임을 반환한다 (검수·디버깅용)."""
    out = frame.copy()
    for a, b in SKELETON:
        if kps[a, 2] < min_conf or kps[b, 2] < min_conf:
            continue
        pa = tuple(int(v) for v in kps[a, :2])
        pb = tuple(int(v) for v in kps[b, :2])
        cv2.line(out, pa, pb, (0, 255, 0), 2)
    for i in range(len(kps)):
        if kps[i, 2] >= min_conf:
            cv2.circle(out, tuple(int(v) for v in kps[i, :2]), 3, (0, 0, 255), -1)
    return out
