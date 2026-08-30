"""영상 → COCO-17 키포인트 시계열.

필수 투입자원 목록에 MediaPipe가 없으므로 **OpenCV + Transformers**로 구성한다.
  - OpenCV: 디코딩, 프레임 샘플링
  - Transformers RT-DETR: 사람 검출 (ViTPose가 top-down 방식이라 필요)
  - Transformers ViTPose: 포즈 추정

판정 모델(EXAONE)과 동시에 GPU에 올리지 않는다. 8GB에서는 순차 실행한다 —
포즈 추출을 끝내고 모델을 해제한 뒤 판정 단계로 넘어간다.
"""

from __future__ import annotations

import base64
import gc
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

# 의존 방향은 pose → observability 한쪽뿐이다 (observability는 표준 라이브러리만
# 쓴다). 반대 방향 import를 추가하면 순환이 되므로 그러지 않는다.
from . import observability

PERSON_DETECTOR = "PekingU/rtdetr_r50vd_coco_o365"
POSE_MODEL = "usyd-community/vitpose-base-simple"
COCO_PERSON_LABEL = 0

# 검출기는 COCO 80클래스를 내는데 지금까지 person만 쓰고 나머지를 버렸다.
# 도구 검출에 새 모델은 필요 없다 — 같은 forward 결과를 재사용하므로 추론 비용이
# 늘지 않는다. 셔틀콕처럼 COCO에 없는 물체는 별도 학습이 필요하다.
TRACKED_LABELS = {
    32: "sports_ball",
    34: "baseball_bat",
    38: "tennis_racket",
}

# 도구 궤적으로 인정할 기준: **확실한 검출이 몇 프레임 있는가**.
#
# 실측 근거(축구·농구 클립 각 1건):
#   축구 공  검출률 39%  중앙값 0.95  0.8이상 46프레임
#   농구 공  검출률 58%  중앙값 0.89  0.8이상 32프레임
#   라켓 오검출          중앙값 0.45  0.8이상  0프레임  ← 두 클립 모두
#
# 최고신뢰도만 보면 농구 클립의 라켓 오검출(0.67)이 통과한다. 검출률만 보면
# 잠깐 보이는 진짜 공을 잃는다. "확실한 프레임이 몇 개는 있어야 한다"가
# 두 클립에서 모두 깨끗하게 갈렸다.
MIN_TOOL_CONFIDENCE = 0.8
MIN_CONFIDENT_FRAMES = 3

# _largest_person_box가 후보로 인정하는 검출 점수 하한.
#
# **이 값은 selector의 동작 기준이므로 바꾸지 않는다.** 여기 상수로 꺼내 둔 것은
# 관측(_count_person_candidates)이 selector와 **같은 후보 집합**을 세게 하려는
# 것뿐이다. 둘이 어긋나면 "후보가 2명인데 selector는 1명만 봤다"는 식으로
# 기록이 실제 동작을 설명하지 못한다. 두 값이 같은지는 테스트가 지킨다.
PERSON_ELIGIBLE_THRESHOLD = 0.5


@dataclass
class PoseResult:
    keypoints: np.ndarray      # (T, 17, 3) — x, y, confidence
    frames: list[np.ndarray]   # 샘플링된 원본 프레임 (오버레이용)
    source_fps: float
    sampled_fps: float         # 실효 샘플링 fps (목표값이 아니라 src_fps / step)
    # 도구 궤적: 이름 → (T, 3) [중심 x, 중심 y, 신뢰도].
    # 미검출 프레임은 신뢰도 0으로 채운다 — 키포인트와 같은 규약이다.
    objects: dict[str, np.ndarray] = field(default_factory=dict)
    # 프레임별 person candidate 수 (raw, eligible). 분석 대상 선택 **이전**의
    # 관측값이며 선택 결과와는 무관하다 — 누가 대상이었는지는 여기서 알 수 없다.
    # 기본값이 빈 리스트라 이 필드를 모르는 기존 호출부는 그대로 동작한다.
    candidate_counts: list[tuple[int, int]] = field(default_factory=list)

    def eligible_candidate_counts(self) -> list[int]:
        """selector가 실제로 후보로 보는 사람 수 (프레임별)."""
        return [e for _, e in self.candidate_counts]

    def raw_candidate_counts(self) -> list[int]:
        """검출기가 person으로 낸 것 전부 (프레임별)."""
        return [r for r, _ in self.candidate_counts]

    def frame_to_seconds(self, frame: int) -> float:
        """샘플링된 프레임 인덱스를 원본 영상의 시각(초)으로 환산한다."""
        return frame / self.sampled_fps

    def object_detection_ratio(self, name: str) -> float:
        """해당 도구가 검출된 프레임 비율. 지표로 쓸 만한지 판단하는 데 쓴다."""
        track = self.objects.get(name)
        if track is None or track.size == 0:
            return 0.0
        return float((track[:, 2] > 0).mean())


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


def _count_person_candidates(
    detections, threshold: float = PERSON_ELIGIBLE_THRESHOLD
) -> tuple[int, int]:
    """프레임 하나에서 person 후보 수를 센다 — (raw, eligible).

    **선택 이전에, 검출 결과가 아직 온전할 때 세야 한다.** _largest_person_box는
    가장 큰 것 하나만 남기고 나머지를 버리므로 그 뒤에는 복원할 수 없다.

    raw       — 검출기가 person으로 낸 것 전부(후처리 임계값을 통과한 것).
    eligible  — 그중 selector가 후보로 인정하는 것(점수 >= threshold).

    detections를 읽기만 하고 바꾸지 않는다. 선택 결과에 영향을 주지 않는다.
    """
    raw = eligible = 0
    for score, label in zip(detections["scores"], detections["labels"]):
        if int(label) != COCO_PERSON_LABEL:
            continue
        raw += 1
        if float(score) >= threshold:
            eligible += 1
    return raw, eligible


def _tracked_centers(detections, threshold: float = 0.3) -> dict[str, tuple[float, float, float]]:
    """프레임 하나에서 관심 도구의 중심좌표를 뽑는다.

    같은 클래스가 여러 개 잡히면 **가장 확실한 것 하나**만 남긴다. 공이 둘일 수는
    없고, 배경의 오검출을 끌고 가는 것보다 낫다. 사람과 달리 크기로 고르지 않는
    이유는 공이 원근에 따라 작아져도 여전히 대상이기 때문이다.
    """
    found: dict[str, tuple[float, float, float]] = {}
    for score, label, box in zip(
        detections["scores"], detections["labels"], detections["boxes"]
    ):
        name = TRACKED_LABELS.get(int(label))
        if name is None or float(score) < threshold:
            continue
        if name in found and found[name][2] >= float(score):
            continue
        x1, y1, x2, y2 = [float(v) for v in box]
        found[name] = ((x1 + x2) / 2.0, (y1 + y2) / 2.0, float(score))
    return found


def _record_input_observation(result: PoseResult, rubric_key: str | None) -> None:
    """입력 분포 관측을 남긴다.

    **기록은 진입점이 아니라 여기서 보장한다.** 관측값(후보 수·fps)이 만들어지는
    곳이 extract_keypoints이고, 서비스 분석이 이 함수를 지나지 않을 수는 없다.
    HTTP 핸들러 쪽에 붙여 두면 새 호출자(job worker 등)가 생길 때마다 사람이
    기억해야 하고, 빠뜨려도 아무 신호가 없다.
    """
    observability.record(
        observability.build_record(
            source_fps=result.source_fps,
            sampled_fps=result.sampled_fps,
            eligible_counts=result.eligible_candidate_counts(),
            raw_counts=result.raw_candidate_counts(),
            rubric_key=rubric_key,
        )
    )


def extract_keypoints(
    video_path: str | Path,
    target_fps: int = 15,
    device: str | None = None,
    observe: bool = True,
    rubric_key: str | None = None,
) -> PoseResult:
    """영상에서 대상 선수의 키포인트 시계열을 추출한다.

    observe — 서비스 입력 관측 레코드를 남길지. **기본값이 True인 것이 핵심이다**:
      새 호출자는 아무것도 하지 않아도 관측에 포함되고, 빠지려면 명시해야 한다.
      CLI·오프라인 평가처럼 서비스 입력이 아닌 경로는 observe=False를 준다
      (scripts/analyze.py, scripts/measure.py).
    rubric_key — 관측 레코드에 붙일 라벨일 뿐이고 포즈 추출에는 쓰이지 않는다.
    """
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
    # 프레임별 person 후보 수 — 사람이 없던 프레임도 (0, 0)으로 채운다.
    # 빠뜨리면 다중인원 비율의 분모가 어긋난다.
    cand_counts: list[tuple[int, int]] = []
    # 프레임마다 도구 검출 결과를 모은다. 사람이 없는 프레임에도 공은 있을 수
    # 있으므로 person 분기와 독립적으로 기록한다.
    obj_frames: list[dict[str, tuple[float, float, float]]] = []

    try:
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            det_inputs = det_processor(images=rgb, return_tensors="pt").to(device)
            with torch.inference_mode():
                det_out = detector(**det_inputs)
            detections = det_processor.post_process_object_detection(
                det_out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3
            )[0]

            obj_frames.append(_tracked_centers(detections))
            # 관측은 선택보다 **먼저** 한다 — 아래에서 후보가 버려지기 때문이다.
            cand_counts.append(_count_person_candidates(detections))

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

    result = PoseResult(
        keypoints=np.stack(all_kps),
        frames=kept_frames,
        source_fps=src_fps,
        sampled_fps=sampled_fps,
        objects=stack_object_tracks(obj_frames),
        candidate_counts=cand_counts,
    )
    if observe:
        _record_input_observation(result, rubric_key)
    return result


def stack_object_tracks(
    per_frame: list[dict[str, tuple[float, float, float]]],
    min_confidence: float = MIN_TOOL_CONFIDENCE,
    min_confident_frames: int = MIN_CONFIDENT_FRAMES,
) -> dict[str, np.ndarray]:
    """프레임별 검출 결과를 도구 이름별 (T, 3) 궤적으로 쌓는다.

    **확실한 검출이 몇 프레임 있는 도구만** 궤적으로 남긴다 (위 상수 주석의
    실측 근거 참고). 오검출은 신뢰도가 낮게 흩어지므로 이 기준에서 걸러진다.

    이동량으로는 거를 수 없다 — 농구 클립의 라켓 오검출은 배경의 정지 물체를
    잡은 것이라 프레임 간 이동(중앙값 6px)이 진짜 공(45px)보다 오히려 작았다.

    미검출 프레임은 (0, 0, 0)이라 신뢰도로 걸러 쓸 수 있다 — 키포인트와 같은 규약.
    """
    names = {n for frame in per_frame for n in frame}
    tracks: dict[str, np.ndarray] = {}
    for name in sorted(names):
        track = np.zeros((len(per_frame), 3))
        for t, frame in enumerate(per_frame):
            if name in frame:
                track[t] = frame[name]
        if int((track[:, 2] >= min_confidence).sum()) < min_confident_frames:
            continue
        tracks[name] = track
    return tracks


# COCO-17 골격 연결 — 오버레이 시각화용
SKELETON = [
    (5, 7), (7, 9), (6, 8), (8, 10),        # 팔
    (5, 6), (5, 11), (6, 12), (11, 12),     # 몸통
    (11, 13), (13, 15), (12, 14), (14, 16),  # 다리
]


def draw_overlay(frame: np.ndarray, kps: np.ndarray, min_conf: float = 0.3) -> np.ndarray:
    """스켈레톤을 그린 프레임을 반환한다 (검수·디버깅용).

    선 두께는 사람 크기에 맞춘다 — 4K 프레임에 2px 선을 그으면 보이지 않는다.
    """
    out = frame.copy()
    scale = max(1, int(round(min(out.shape[:2]) / 480)))

    for a, b in SKELETON:
        if kps[a, 2] < min_conf or kps[b, 2] < min_conf:
            continue
        pa = tuple(int(v) for v in kps[a, :2])
        pb = tuple(int(v) for v in kps[b, :2])
        cv2.line(out, pa, pb, (0, 255, 0), 2 * scale, cv2.LINE_AA)
    for i in range(len(kps)):
        if kps[i, 2] >= min_conf:
            cv2.circle(out, tuple(int(v) for v in kps[i, :2]),
                       3 * scale, (0, 0, 255), -1, cv2.LINE_AA)
    return out


def crop_to_person(
    frame: np.ndarray, kps: np.ndarray, min_conf: float = 0.3, margin: float = 0.35
) -> np.ndarray:
    """대상 선수 주변만 잘라낸다.

    전신이 화면의 일부만 차지하는 원본을 그대로 축소하면 자세가 안 보인다.
    유효 키포인트의 경계상자에 여백을 붙여 자른다.
    """
    valid = kps[kps[:, 2] >= min_conf, :2]
    if len(valid) < 2:
        return frame

    h, w = frame.shape[:2]
    x1, y1 = valid.min(axis=0)
    x2, y2 = valid.max(axis=0)
    pad = margin * max(x2 - x1, y2 - y1)

    x1 = max(0, int(x1 - pad))
    y1 = max(0, int(y1 - pad))
    x2 = min(w, int(x2 + pad))
    y2 = min(h, int(y2 + pad))
    if x2 - x1 < 10 or y2 - y1 < 10:
        return frame
    return frame[y1:y2, x1:x2]


def _subject_windows(
    keypoints: np.ndarray, shape: tuple[int, int], min_conf: float, margin: float, smooth: int
) -> tuple[list[tuple[int, int]], int, int]:
    """프레임별 크롭 좌상단 좌표와 고정 크롭 크기를 계산한다.

    크롭 크기를 클립 내내 고정하고 중심만 움직인다 — 크기가 프레임마다 바뀌면
    화면이 확대·축소를 반복해 보기 어렵다. 중심은 이동평균으로 눌러 흔들림을
    줄인다(카메라가 선수를 따라가는 느낌).
    """
    h, w = shape
    centers: list[np.ndarray | None] = []
    sizes: list[float] = []
    for kps in keypoints:
        valid = kps[kps[:, 2] >= min_conf, :2]
        if len(valid) < 2:
            centers.append(None)
            continue
        lo, hi = valid.min(axis=0), valid.max(axis=0)
        centers.append((lo + hi) / 2.0)
        sizes.append(float(max(hi - lo)))

    if not sizes:
        return [(0, 0)] * len(keypoints), w, h

    # 검출 실패 구간은 가장 가까운 유효 중심으로 채운다.
    known = [i for i, c in enumerate(centers) if c is not None]
    filled = [centers[min(known, key=lambda k: abs(k - i))] for i in range(len(centers))]

    arr = np.stack(filled)
    if smooth > 1:
        pad = smooth // 2
        padded = np.pad(arr, ((pad, pad), (0, 0)), mode="edge")
        kernel = np.ones(smooth) / smooth
        arr = np.stack([np.convolve(padded[:, d], kernel, mode="valid")[: len(arr)]
                        for d in range(2)], axis=1)

    side = int(min(max(sizes) * (1.0 + margin), min(h, w)))
    cw = ch = max(side, 64)

    tops: list[tuple[int, int]] = []
    for cx, cy in arr:
        x = int(np.clip(cx - cw / 2, 0, max(0, w - cw)))
        y = int(np.clip(cy - ch / 2, 0, max(0, h - ch)))
        tops.append((x, y))
    return tops, cw, ch


def render_tracked_clip(
    frames: list[np.ndarray],
    keypoints: np.ndarray,
    out_path: Path,
    fps: float,
    impact: int | None = None,
    out_width: int = 640,
    min_conf: float = 0.3,
    margin: float = 0.6,
    smooth: int = 9,
) -> dict:
    """대상 선수를 따라가는 스켈레톤 영상을 만든다.

    **추가 추론이 없다.** 포즈 추출 때 이미 얻은 프레임과 키포인트만 쓴다.

    코덱은 VP8/WebM이다 — OpenCV의 pip 빌드에는 H.264 인코더가 없고(라이선스),
    mp4v는 브라우저가 재생하지 못한다. WebM은 브라우저가 기본 지원한다.
    """
    if not frames:
        raise ValueError("프레임이 없습니다")

    h, w = frames[0].shape[:2]
    tops, cw, ch = _subject_windows(keypoints, (h, w), min_conf, margin, smooth)

    ow = out_width
    oh = int(round(ow * ch / cw / 2) * 2)      # 짝수 — 인코더가 요구한다
    writer = cv2.VideoWriter(
        str(out_path), cv2.VideoWriter_fourcc(*"VP80"), max(1.0, fps), (ow, oh)
    )
    if not writer.isOpened():
        raise RuntimeError(f"인코더를 열 수 없습니다: {out_path}")

    try:
        for t, frame in enumerate(frames):
            canvas = draw_overlay(frame, keypoints[t], min_conf)
            x, y = tops[t]
            crop = canvas[y : y + ch, x : x + cw]
            if crop.size == 0:
                crop = canvas
            crop = cv2.resize(crop, (ow, oh), interpolation=cv2.INTER_AREA)

            if impact is not None and t == impact:
                cv2.rectangle(crop, (0, 0), (ow - 1, oh - 1), (0, 0, 255), 6)
                cv2.putText(crop, "IMPACT", (14, 34), cv2.FONT_HERSHEY_SIMPLEX,
                            0.9, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(crop, f"{t}", (14, oh - 14), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (240, 240, 240), 2, cv2.LINE_AA)
            writer.write(crop)
    finally:
        writer.release()

    return {"frames": len(frames), "size": (ow, oh), "fps": fps,
            "bytes": out_path.stat().st_size if out_path.exists() else 0}


def encode_preview(frame: np.ndarray, max_width: int = 720, quality: int = 85) -> str:
    """프레임을 data URI(JPEG)로 인코딩한다.

    JSON에 실어 보내므로 폭을 제한한다 — 4K 원본을 그대로 넣으면 응답이 수 MB가
    되고 브라우저가 버벅인다. 내용이 사진이라 PNG는 비효율적이다(실측 822KB →
    JPEG 85로 10분의 1 수준). 스켈레톤 선이 굵어 JPEG 압축에도 뭉개지지 않는다.
    """
    if frame.shape[1] > max_width:
        ratio = max_width / frame.shape[1]
        frame = cv2.resize(
            frame, (max_width, int(frame.shape[0] * ratio)), interpolation=cv2.INTER_AREA
        )
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG 인코딩 실패")
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")
