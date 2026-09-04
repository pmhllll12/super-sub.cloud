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
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

# 의존 방향은 pose → observability 한쪽뿐이다 (observability는 표준 라이브러리만
# 쓴다). 반대 방향 import를 추가하면 순환이 되므로 그러지 않는다.
from . import observability

# 표준 logging만 쓴다 — observability.py 와 같은 규약이다.
_log = logging.getLogger(__name__)

PERSON_DETECTOR = "PekingU/rtdetr_r50vd_coco_o365"
POSE_MODEL = "usyd-community/vitpose-base-simple"
COCO_PERSON_LABEL = 0

# 샘플링 목표 fps의 **단일 진실원**. 서비스도 평가도 이 값을 쓴다.
#
# 15에서 30으로 올렸다(2026-09-02). 15fps에서는 임팩트가 실제로 일어난 프레임이
# 격자에 없는 경우가 많아 **측정 자체가 성립하지 않았다** — 밴드 적중 31.8%가
# 30fps에서 49.8%로 올라간다. 더 정확해진 것이 아니라 **다른 프레임을 고르게
# 된 것**이고, 어느 쪽이 옳은지는 정답이 있어야 말할 수 있다(미결 5번 보류).
# 60까지 올려도 +3.7pp뿐이고 평가셋 39클립 중 38건이 30fps 이하라 30에서 멈춘다.
#
# 평가 스크립트가 리터럴 15를 들고 있어서 서비스와 갈라져 있었다(미결 10번).
# 리터럴을 쓰지 말고 이 상수를 import해서 쓸 것 — 값이 바뀌면 같이 따라와야
# 평가가 서비스의 동작점을 재는 의미가 있다.
DEFAULT_TARGET_FPS = 30

# **분석 창(초).** 몇 초까지 볼 것인가 — 소스 fps와 무관한 값이다.
# 10.0인 이유: 현재 동작점(target 30, step 1)에서 300장이 정확히 10.0초라
# 기존 동작을 그대로 보존한다. 평가셋 39클립이 전부 10초 이하라 무변화다.
DEFAULT_MAX_SECONDS = 10.0

# **메모리 가드(장).** 분석 의도가 아니라 미결 9번(4K에서 host RAM이 먼저
# 터진다)이 정한 상한이다. 4K 300장이 약 7GB이고 g4dn.xlarge의 host RAM은
# 16GB다. 창을 넓히고 싶으면 DEFAULT_MAX_SECONDS를 올릴 것 — 이 값을 올리면
# 메모리 한계를 올리는 것이지 창을 넓히는 것이 아니다.
DEFAULT_MAX_FRAMES = 300

# 실효 fps가 목표의 이 비율보다 낮으면 경고한다. **절벽만 막는다** —
# 미결 7번이 확인했듯 30↔60에서도 등급이 37% 바뀌므로, 이 경고가 fps 불변성을
# 뜻하지는 않는다.
#
# 0.75인 이유: target 30에서 한계가 22.5fps다. **0.8(=24.0)로 두면 NTSC 24인
# 23.976fps가 아슬아슬하게 걸린다** — 평가셋에 실제로 있고 흔한 소스다.
# 흔한 입력이 매번 경고를 내면 그 경고는 읽히지 않게 된다. 24 계열은 통과하고
# 10fps 같은 절벽은 걸리는 자리가 0.75다.
LOW_FPS_WARN_RATIO = 0.75

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

# 사람이 찍은 박스가 그 후보를 가리킨다고 볼 최소 IoU (미결 18번).
#
# **임시값이다.** 손으로 그린 네모는 검출 박스보다 헐겁게 잡히므로(화면의
# 예시가 그렇다) 완전 일치를 요구할 수 없고, 그렇다고 0으로 두면 화면 반대편
# 사람도 "찍은 사람"이 된다. 0.3은 그 사이에서 흔히 쓰는 값이다.
#
# 🔴 **이 값을 고르는 근거는 아직 없다.** 그래서 실제 IoU를 결과와 관측에
# 남긴다(`SubjectSelection.anchor_iou`) — 분포가 쌓이면 그때 다시 본다.
# 값 자체보다 **못 맞췄을 때 조용히 넘어가지 않는 것**이 이 기능의 요점이다.
MIN_ANCHOR_IOU = 0.3


@dataclass(frozen=True)
class SubjectRequest:
    """사람이 지정한 분석 대상 — 어느 사람을, 언제 찍었는가.

    box는 **정규화 0~1**의 (x, y, w, h)다. 표시 해상도가 아니라 원본 기준이며
    레터박스 여백은 프론트가 이미 걷어낸다(`toVideoBox`). 픽셀로 받으면
    화면 크기가 다른 기기에서 조용히 어긋난다 — 계약에 정규화라고 못박는다.

    at_ms는 그 박스를 그린 순간의 영상 시각(밀리초)이다. 🔴 **그 순간이 샘플
    격자에 없을 수 있다** — `step`으로 솎기 때문이다. 가장 가까운 프레임에
    붙이고 어긋난 정도를 기록한다(`SubjectSelection.grid_offset_frames`).
    """

    box: tuple[float, float, float, float]
    at_ms: float


@dataclass(frozen=True)
class SubjectSelection:
    """대상을 **어떻게** 골랐는가. 결과와 관측에 그대로 실린다.

    🔴 **이것이 없으면 "찍은 사람이 실제로 분석됐는가"를 확인할 방법이 없다.**
    `candidate_counts`는 선택 *이전* 관측이라 누가 대상이었는지를 모른다.
    특히 ViTPose는 top-down이라 **엉뚱한 박스를 줘도 자신 있게 관절을 낸다** —
    신뢰도로는 드러나지 않으므로 선택 자체를 남겨야 한다.
    """

    # "auto"      — 지정이 없었다. 지금까지의 동작(`_largest_person_box`).
    # "specified" — 지정한 자리에서 후보를 찾아 그 사람을 따라갔다.
    # "fallback"  — 지정은 있었으나 못 맞춰 자동으로 떨어졌다.
    #               🔴 조용히 떨어지면 사용자는 자기가 찍은 대로 분석된 줄 안다.
    source: str = "auto"
    why: str = ""
    anchor_frame: int | None = None
    anchor_iou: float | None = None
    # 지정 시각과 실제 격자 프레임의 어긋남(프레임). 최대 step/2다.
    grid_offset_frames: float | None = None
    # 지정 시각이 분석 창 밖이라 끝으로 당겨졌는가 (업로드 60초 대 창 10초).
    clamped: bool = False
    # 이어가다 겹치는 후보가 없어 연속성을 끊은 프레임 수.
    continuity_breaks: int = 0

    @property
    def used_specification(self) -> bool:
        return self.source == "specified"


# 인접 프레임에서 선택 박스 넓이가 이 배수 이상 뛰면 **대상이 바뀐 것으로 의심**한다.
#
# 🔴 **막는 값이 아니라 세는 값이다.** 사람이 카메라 쪽으로 다가오면 넓이는 실제로
# 커지므로, 이것으로 후보를 거르면 정상 동작을 막는다. 그래서 선택에는 관여하지
# 않고 **몇 번 뛰었는지만** 결과·관측에 남긴다.
#
# 왜 필요한가: `continuity_breaks`가 **이 실패를 못 잡는다.** 그쪽은 "겹치는 후보가
# 하나도 없다"를 세는데, 신원이 바뀔 때는 겹침이 넉넉하다. 실제로 `3R1kvNrGJK0`
# 에서 타자를 따라가던 트랙이 110프레임에서 심판으로 갈아탔는데 끊김은 0이었고,
# 그 뒤 190프레임(63%)을 다른 사람으로 분석했다. **그 자리의 넓이비가 5.5배**라
# 이 신호는 정확히 한 번, 갈아탄 프레임에서만 걸렸다(같은 클립의 자동 트랙은 0회).
#
# 2.0인 근거는 **그 사례 하나뿐이다.** 한 클립에서 맞았다고 검증된 것이 아니다 —
# 분포가 쌓이면 다시 본다.
SUBJECT_AREA_JUMP = 2.0


def count_area_jumps(
    boxes: list[tuple[float, float, float, float] | None],
    factor: float = SUBJECT_AREA_JUMP,
) -> int:
    """인접 프레임 사이에서 선택 박스 넓이가 크게 뛴 횟수.

    **대상이 바뀌었을 가능성의 신호다.** 확정이 아니다 — 원근으로도 커진다.
    둘 중 하나가 없는 프레임은 건너뛴다(그건 `continuity_breaks` 쪽 이야기다).
    """
    jumps = 0
    for before, after in zip(boxes, boxes[1:]):
        if before is None or after is None:
            continue
        a = before[2] * before[3]
        b = after[2] * after[3]
        if a <= 0 or b <= 0:
            continue
        if max(a, b) / min(a, b) >= factor:
            jumps += 1
    return jumps


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """두 xywh 박스의 IoU. 겹치지 않으면 0이다."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return float(inter / union) if union > 0 else 0.0


@dataclass
class PoseResult:
    """분석 결과. **원본 프레임은 들고 있지 않는다.**

    프레임은 채점에 전혀 쓰이지 않는다 — extract_features는 키포인트와 도구
    궤적만 받는다. 쓰이는 곳은 미리보기 렌더링뿐인데, 그것은 판정이 끝난 뒤에
    일어난다. 그런데도 프레임을 들고 있으면 4K 300장(≈7GB)이 포즈 추출부터
    판정 모델 적재까지 내내 메모리에 남는다. 그래서 **다시 얻는 방법**만
    들고 있다가 렌더링 시점에 재디코딩한다(`load_frames`).
    """

    keypoints: np.ndarray      # (T, 17, 3) — x, y, confidence
    source_fps: float
    sampled_fps: float         # 실효 샘플링 fps (목표값이 아니라 src_fps / step)
    # 프레임을 다시 얻는 데 필요한 것. video_path가 None이면 프레임이 없는
    # 결과다(합성 키포인트 경로) — load_frames()가 None을 돌려준다.
    video_path: str | None = None
    target_fps: int = DEFAULT_TARGET_FPS   # 추출 때 쓴 값. 재디코딩이 같은 프레임을 골라야 한다.
    # 상한도 함께 들고 다닌다. 재디코딩이 **같은 장수**를 잘라야 하기 때문이다 —
    # 추출은 좁은 창으로 하고 재디코딩만 기본값으로 하면 미리보기가 키포인트보다
    # 길어져 프레임과 인덱스가 어긋난다. 기본값을 쓰면 기존 호출부는 그대로다.
    max_frames: int = DEFAULT_MAX_FRAMES
    max_seconds: float = DEFAULT_MAX_SECONDS
    # 도구 궤적: 이름 → (T, 3) [중심 x, 중심 y, 신뢰도].
    # 미검출 프레임은 신뢰도 0으로 채운다 — 키포인트와 같은 규약이다.
    objects: dict[str, np.ndarray] = field(default_factory=dict)
    # 프레임별 person candidate 수 (raw, eligible). 분석 대상 선택 **이전**의
    # 관측값이며 선택 결과와는 무관하다 — 누가 대상이었는지는 여기서 알 수 없다.
    # 기본값이 빈 리스트라 이 필드를 모르는 기존 호출부는 그대로 동작한다.
    candidate_counts: list[tuple[int, int]] = field(default_factory=list)
    # 프레임별로 **실제 분석한 사람의 박스** (원 픽셀 xywh). 못 고른 프레임은 None.
    # candidate_counts 가 선택 *이전*이라면 이쪽은 선택 *결과*다 — 둘 다 있어야
    # "몇 명 중에 누구를 봤는가"가 사후에 확인된다 (미결 8번·18번).
    subject_boxes: list[tuple[float, float, float, float] | None] = field(
        default_factory=list
    )
    # 위 박스를 어떤 좌표계에서 읽어야 하는지 — (너비, 높이) 픽셀.
    # 없으면 정규화해 내보낼 수 없다.
    frame_size: tuple[int, int] | None = None
    # 대상을 어떻게 골랐는가. 기본값은 지금까지의 동작(auto)이라 이 필드를
    # 모르는 기존 호출부가 그대로 맞다.
    subject_selection: SubjectSelection = field(default_factory=SubjectSelection)

    def subject_box_frames(self) -> int:
        """대상을 실제로 고른 프레임 수."""
        return sum(1 for b in self.subject_boxes if b is not None)

    def normalized_subject_boxes(self) -> list[list[float] | None]:
        """선택 박스를 정규화 0~1로. 프레임 크기를 모르면 전부 None이다.

        프론트가 보내는 좌표계와 **같은 좌표계로 돌려준다** — 그래야 "찍은
        박스와 실제로 분석한 박스"의 IoU를 화면 크기 없이 바로 잴 수 있다.
        """
        if not self.frame_size:
            return [None] * len(self.subject_boxes)
        w, h = self.frame_size
        if w <= 0 or h <= 0:
            return [None] * len(self.subject_boxes)
        out: list[list[float] | None] = []
        for box in self.subject_boxes:
            if box is None:
                out.append(None)
                continue
            x, y, bw, bh = box
            out.append([round(x / w, 6), round(y / h, 6),
                        round(bw / w, 6), round(bh / h, 6)])
        return out

    def eligible_candidate_counts(self) -> list[int]:
        """selector가 실제로 후보로 보는 사람 수 (프레임별)."""
        return [e for _, e in self.candidate_counts]

    def raw_candidate_counts(self) -> list[int]:
        """검출기가 person으로 낸 것 전부 (프레임별)."""
        return [r for r, _ in self.candidate_counts]

    def load_frames(self) -> list[np.ndarray] | None:
        """오버레이용 원본 프레임을 그 자리에서 다시 디코딩한다.

        **같은 프레임이 나오는 근거는 read_frames가 결정적이라는 것뿐이다** —
        경로·target_fps·상한이 같으면 같은 인덱스(idx % step == 0)를 같은 개수만큼
        고른다. 그래서 추출 때 쓴 값들을 결과가 함께 들고 다닌다. 파일이 사라진
        뒤에 부르면 read_frames가 그대로 예외를 낸다(업로드 임시 파일 수명 주의).

        재디코딩 비용은 포즈 추출(모델 적재 제외)의 10% 수준이다 — 실측
        1080p 11.3ms/장 대 104.6ms/장, 4K 34.2ms/장 대 351.1ms/장.
        프레임이 없는 결과(합성 경로)에서는 None을 돌려준다.
        """
        if self.video_path is None:
            return None
        frames, _, _ = read_frames(
            self.video_path, self.target_fps, self.max_frames, self.max_seconds
        )
        return frames

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
    video_path: str | Path,
    target_fps: int = DEFAULT_TARGET_FPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
    max_seconds: float = DEFAULT_MAX_SECONDS,
) -> tuple[list[np.ndarray], float, float]:
    """OpenCV로 디코딩하고 target_fps에 가장 가까운 정수 간격으로 다운샘플링한다.

    반환값은 (프레임, 원본 fps, **실효** 샘플링 fps)다.

    간격이 정수라 target_fps를 그대로 달성하지 못한다 — 25fps 영상에 target 15를
    주면 step=round(1.67)=2, 즉 실효 12.5fps다. 목표값을 실효값인 양 기록하면
    프레임 인덱스를 시각으로 환산할 때 20% 어긋난다.

    **상한이 둘이고 역할이 다르다** (미결 7번 「인접 결함 두 건」).

      max_seconds — **분석 창.** 몇 초까지 볼 것인가. 소스 fps와 무관하다.
      max_frames  — **메모리 가드.** 몇 장까지 들 것인가. 미결 9번(4K에서 host
                    RAM이 먼저 터진다)이 정한 값이며 분석 의도가 아니다.

    프레임 수만으로 막으면 **덮는 실시간 길이가 fps에 따라 달라진다** — 300장은
    30fps에서 10.0초지만 24fps에서는 12.5초다. 같은 동작을 담은 두 인코딩이 서로
    다른 구간을 분석하게 되고, 그 차이는 아무 데도 기록되지 않는다. 그래서 창은
    초로 정하고 프레임 수는 자원 보호로만 남긴다.

    둘 중 **먼저 걸리는 쪽**이 이긴다. 실효 fps가 목표를 넘는 소스(40fps에
    target 30이면 step=1이라 실효 40fps)에서는 초 예산이 프레임 예산을 넘어서므로
    메모리 가드가 필요하다.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(src_fps / target_fps))
    sampled_fps = src_fps / step

    # t < max_seconds 인 프레임의 개수. k 번째 표본의 시각이 k / sampled_fps 이므로
    # k < max_seconds * sampled_fps 이고, 개수는 그 값의 올림이다.
    # (내림을 쓰면 29.97fps·10초에서 299장이 되어 300장이던 기존 동작이 조용히
    #  한 장 줄어든다. 경계에서 동작이 바뀌지 않게 올림을 쓴다.)
    # math.inf 는 "창 제한 없음"이다 — 메모리 가드만 남긴다. ceil(inf)가
    # OverflowError 를 내므로 먼저 걸러낸다.
    if math.isfinite(max_seconds):
        limit = min(max_frames, max(1, math.ceil(max_seconds * sampled_fps)))
    else:
        limit = max_frames

    if sampled_fps < target_fps * LOW_FPS_WARN_RATIO:
        _log.warning(
            "실효 샘플링 fps가 목표보다 크게 낮습니다: %.2f < %d (소스 %.2ffps, step %d). "
            "프레임 간격이 넓어 임팩트 추정이 거칠어집니다. "
            "이 경고는 절벽만 막으며 fps 불변성을 보장하지 않습니다 (미결 7번).",
            sampled_fps, target_fps, src_fps, step,
        )

    frames: list[np.ndarray] = []
    idx = 0
    while len(frames) < limit:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            frames.append(frame)
        idx += 1
    cap.release()

    if not frames:
        raise ValueError(f"프레임을 읽지 못했습니다: {video_path}")
    return frames, src_fps, sampled_fps


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


def _eligible_person_boxes(
    detections, threshold: float = PERSON_ELIGIBLE_THRESHOLD
) -> list[tuple[float, float, float, float]]:
    """프레임 하나의 person 후보 박스 전부 (xywh).

    `_largest_person_box`는 가장 큰 것 하나만 남기고 나머지를 **버린다.**
    사람이 찍은 자리와 맞춰 보려면 버려지기 전 목록이 필요하다.
    임계값을 selector와 같은 상수로 두어 "후보"의 뜻이 갈리지 않게 한다.
    """
    out: list[tuple[float, float, float, float]] = []
    for score, label, box in zip(
        detections["scores"], detections["labels"], detections["boxes"]
    ):
        if int(label) != COCO_PERSON_LABEL or float(score) < threshold:
            continue
        x1, y1, x2, y2 = [float(v) for v in box]
        out.append((x1, y1, x2 - x1, y2 - y1))
    return out


def anchor_frame_for(at_ms: float, sampled_fps: float, frame_count: int) -> tuple[int, float, bool]:
    """지정 시각을 **샘플 격자의 프레임 인덱스**로 옮긴다.

    돌려주는 것은 (프레임, 격자 어긋남, 창 밖이었는가)다.

    `labeling/targets.py:remap_label_frame`과 같은 산술의 다른 방향이다 —
    저쪽은 격자→격자이고 이쪽은 시각→격자인데 **같은 함정을 공유한다**:
    그 순간이 격자에 없을 수 있다. 🔴 **저쪽은 예외를 던지지만 여기서는
    던지지 않는다** — 서비스가 사용자의 클릭 하나로 분석을 통째로 거부하면
    안 된다. 가장 가까운 프레임에 붙이고 **어긋난 정도를 돌려준다.**

    창 밖(업로드 60초 대 분석 창 10초)이면 끝 프레임으로 당기고 그 사실을
    함께 돌려준다. 조용히 당기면 사용자는 자기가 찍은 순간이 분석된 줄 안다.
    """
    if frame_count <= 0:
        raise ValueError("프레임이 없다")
    if not sampled_fps or not math.isfinite(sampled_fps) or sampled_fps <= 0:
        raise ValueError(f"실효 fps를 모른다: {sampled_fps!r}")

    exact = (at_ms / 1000.0) * sampled_fps
    # 정확히 절반인 지점은 **뒤쪽으로** 붙인다(round-half-up). 파이썬 기본
    # `round`는 짝수로 붙어서(banker's rounding) 12.5→12, 13.5→14가 된다 —
    # 같은 0.5인데 방향이 갈리면 왜 그 프레임인지 설명할 수 없다.
    snapped = math.floor(exact + 0.5)
    clamped = not (0 <= snapped < frame_count)
    frame = max(0, min(frame_count - 1, snapped))
    return frame, round(abs(exact - snapped), 3), clamped


def select_subject_boxes(
    auto_boxes: list[tuple[float, float, float, float] | None],
    candidates: list[list[tuple[float, float, float, float]]],
    subject: SubjectRequest | None,
    sampled_fps: float,
    frame_size: tuple[int, int],
) -> tuple[list[tuple[float, float, float, float] | None], SubjectSelection]:
    """프레임별로 분석할 사람의 박스를 정한다.

    🔴 **지정이 없으면 `auto_boxes`를 그대로 돌려준다** — 목록을 새로 만들지
    않고 같은 값을 넘긴다. 그래야 지정이 없을 때 ViTPose 입력이 **한 비트도
    달라지지 않고**, 기존 평가(B-1~B-6)와의 비교가 끊기지 않는다.

    지정이 있으면 두 단계다.

      1. **닻** — 찍은 프레임에서 찍은 박스와 IoU가 가장 큰 후보를 고른다.
         `MIN_ANCHOR_IOU`에 못 미치면 **못 맞춘 것**이고 자동으로 떨어진다.
      2. **이어가기** — 닻에서 앞뒤로, 직전에 고른 박스와 IoU가 가장 큰 후보를
         고른다. 겹치는 후보가 하나도 없으면 **연속성을 끊고** 그 프레임은
         자동 선택을 쓴다(`eval_selectors.py`가 후보 0개에서 정한 것과 같은
         처리다). 끊긴 횟수를 세어 남긴다.

    ⚠️ **이 규칙은 오프라인 평가가 잰 규칙이 아니다.** B-1~B-6은 지정이 없는
    39클립에서 `_largest_person_box`를 쟀다. 여기 이어가기 수식은
    `eval_selectors.py`의 가중합을 **옮겨 온 것이 아니다** — 그 파일은 일부러
    만든 복제본이고 그 가중치는 production 값이 아니다(미결 10번이 낸 사고의
    형태). 지정 경로는 새 경로이며 평가가 그것을 잰 적이 없다.
    """
    if subject is None:
        return auto_boxes, SubjectSelection(source="auto")

    n = len(auto_boxes)
    width, height = frame_size
    x, y, w, h = subject.box
    pixel_box = (x * width, y * height, w * width, h * height)

    try:
        anchor, offset, clamped = anchor_frame_for(subject.at_ms, sampled_fps, n)
    except ValueError as exc:
        return auto_boxes, SubjectSelection(
            source="fallback", why=f"지정 시각을 프레임으로 옮길 수 없다 ({exc})"
        )

    here = candidates[anchor] if anchor < len(candidates) else []
    best_iou, best_box = 0.0, None
    for cand in here:
        iou = _iou(pixel_box, cand)
        if iou > best_iou:
            best_iou, best_box = iou, cand

    if best_box is None or best_iou < MIN_ANCHOR_IOU:
        return auto_boxes, SubjectSelection(
            source="fallback",
            why=(f"찍은 자리({anchor}프레임)에서 그 사람을 못 찾았다 — "
                 f"후보 {len(here)}개, 최대 IoU {best_iou:.2f} < {MIN_ANCHOR_IOU}"),
            anchor_frame=anchor,
            anchor_iou=round(best_iou, 3),
            grid_offset_frames=offset,
            clamped=clamped,
        )

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = best_box
    breaks = 0

    def walk(order, seed):
        nonlocal breaks
        previous = seed
        for t in order:
            pick, pick_iou = None, 0.0
            for cand in candidates[t]:
                iou = _iou(previous, cand)
                if iou > pick_iou:
                    pick, pick_iou = cand, iou
            if pick is None:
                # 겹치는 후보가 없다 — 이어갈 근거가 사라졌다.
                # 직전 박스를 계속 들고 가면 그 오류를 굳히게 되므로 끊는다.
                breaks += 1
                chosen[t] = auto_boxes[t]
                if auto_boxes[t] is not None:
                    previous = auto_boxes[t]
                continue
            chosen[t] = pick
            previous = pick

    walk(range(anchor + 1, n), best_box)
    walk(range(anchor - 1, -1, -1), best_box)

    return chosen, SubjectSelection(
        source="specified",
        anchor_frame=anchor,
        anchor_iou=round(best_iou, 3),
        grid_offset_frames=offset,
        clamped=clamped,
        continuity_breaks=breaks,
    )


def parse_subject_spec(box: str | None, at_ms: float | None) -> SubjectRequest | None:
    """`"x,y,w,h"` 문자열과 시각을 SubjectRequest로. 잘못되면 ValueError.

    **규칙을 여기 한 곳에 둔다.** HTTP는 422로, CLI는 종료 코드로 갈리지만
    "무엇이 올바른 지정인가"는 하나여야 한다 — 두 곳에 복사하면 한쪽만
    고쳐졌을 때 같은 입력이 경로에 따라 통과했다 막혔다 한다(미결 10번의 형태).

    🔴 **범위를 벗어난 좌표는 거부한다.** 화면 픽셀을 그대로 보내면 값이
    1을 넘는데, 그것을 조용히 받아 클램프하면 **엉뚱한 사람을 분석하고도
    "지정대로 했다"고 답하게 된다.** 그것이 가장 나쁜 실패다.
    """
    if box is None:
        return None
    parts = [p.strip() for p in box.split(",")]
    if len(parts) != 4:
        raise ValueError("subject_box는 'x,y,w,h' 네 값이어야 한다 (정규화 0~1)")
    try:
        x, y, w, h = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError(f"subject_box를 숫자로 읽을 수 없다: {box!r}") from exc
    if w <= 0 or h <= 0:
        raise ValueError("subject_box의 너비·높이는 0보다 커야 한다")
    if not all(0.0 <= v <= 1.0 for v in (x, y, x + w, y + h)):
        raise ValueError(
            "subject_box는 정규화 0~1이어야 한다 — 화면 픽셀 좌표를 보낸 것이 "
            f"아닌지 확인할 것 (받은 값: {box!r})"
        )
    if at_ms is None:
        raise ValueError("subject_box를 주면 subject_at_ms도 함께 주어야 한다")
    if at_ms < 0:
        raise ValueError("subject_at_ms는 0 이상이어야 한다")
    return SubjectRequest(box=(x, y, w, h), at_ms=float(at_ms))


def subject_envelope(result: "PoseResult | None", frame_count: int) -> dict:
    """**누구를 분석했는가** — 선택 박스 시계열과 어떻게 골랐는지 (미결 18번).

    🔴 이것이 없으면 "찍은 사람이 실제로 분석됐는가"를 확인할 방법이 없다.
    `candidate_counts`는 선택 **이전** 관측이고, ViTPose는 top-down이라
    **엉뚱한 박스를 줘도 자신 있게 관절을 낸다** — 신뢰도로는 드러나지 않는다.
    박스가 남아 있으면 (1) 지정 박스와의 IoU를 기계적으로 재고
    (2) `render_tracked_clip`으로 눈으로 본다.

    🔴 **`features`를 바꾸지 않는다.** `timebase`와 같은 형제 블록이라 판정
    입력이 그대로다 — 기존 평가(B-2~B-6)와 비교가 끊기지 않는다.

    박스는 **정규화 0~1**로 낸다. 프론트가 보내는 좌표계와 같아야 화면 크기를
    몰라도 바로 대조된다. 픽셀로 되짚을 수 있게 `frame_size`를 함께 싣는다.

    HTTP 응답과 S3 리포트가 **같은 함수를 쓴다** — 두 벌로 두면 한쪽에만
    필드가 늘어나 "어느 경로로 낸 결과냐"에 따라 봉투가 달라진다.
    """
    if result is None:
        return {
            "known": False,
            "why": "합성 키포인트 경로 — 영상이 없어 사람 박스가 존재하지 않는다",
            "source": "auto",
        }

    selection = result.subject_selection
    return {
        "known": True,
        # "auto" | "specified" | "fallback"
        # 🔴 fallback을 조용히 넘기지 않는다 — 사용자는 자기가 찍은 대로
        # 분석된 줄 안다. why에 못 맞춘 이유가 들어 있다.
        "source": selection.source,
        "why": selection.why,
        "anchor_frame": selection.anchor_frame,
        "anchor_iou": selection.anchor_iou,
        # 지정 시각과 샘플 격자의 어긋남(프레임). 최대 step/2다.
        "grid_offset_frames": selection.grid_offset_frames,
        # 찍은 시각이 분석 창 밖이라 끝으로 당겨졌는가.
        "at_clamped": selection.clamped,
        "continuity_breaks": selection.continuity_breaks,
        # 🔴 **끊김 0이 "잘 따라갔다"는 뜻이 아니다.** 신원이 바뀔 때는 겹침이
        # 넉넉해서 끊김으로 안 잡힌다. 넓이가 크게 뛴 횟수를 함께 낸다 —
        # 확정이 아니라 의심 신호다(count_area_jumps).
        "area_jumps": count_area_jumps(result.subject_boxes),
        "frame_size": list(result.frame_size) if result.frame_size else None,
        "frames_with_box": result.subject_box_frames(),
        "frames": frame_count,
        # (x, y, w, h) 정규화. 못 고른 프레임은 null이다.
        "boxes": result.normalized_subject_boxes(),
    }


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
            # 대상을 **어떻게** 골랐는가. 이것이 있어야 "사람 지정이 얼마나
            # 자주 실패하는가"를 정답 없이 잰다 (미결 18번 → 12번).
            subject=result.subject_selection,
            subject_box_frames=result.subject_box_frames(),
            subject_area_jumps=count_area_jumps(result.subject_boxes),
        )
    )


def extract_keypoints(
    video_path: str | Path,
    target_fps: int = DEFAULT_TARGET_FPS,
    device: str | None = None,
    observe: bool = True,
    rubric_key: str | None = None,
    max_frames: int = DEFAULT_MAX_FRAMES,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    subject: SubjectRequest | None = None,
) -> PoseResult:
    """영상에서 대상 선수의 키포인트 시계열을 추출한다.

    subject — 사람이 찍은 분석 대상(정규화 박스 + 시각). **None이면 지금까지의
      동작 그대로**이고 결과가 한 비트도 달라지지 않는다. `side`와 같은 규칙이다:
      사람이 지정할 수 있게 열어 두고, 없으면 자동으로 고른다. 못 맞추면
      자동으로 떨어지되 **그 사실이 결과에 남는다**(`subject_selection`).

    observe — 서비스 입력 관측 레코드를 남길지. **기본값이 True인 것이 핵심이다**:
      새 호출자는 아무것도 하지 않아도 관측에 포함되고, 빠지려면 명시해야 한다.
      CLI·오프라인 평가처럼 서비스 입력이 아닌 경로는 observe=False를 준다
      (scripts/analyze.py, scripts/measure.py).
    rubric_key — 관측 레코드에 붙일 라벨일 뿐이고 포즈 추출에는 쓰이지 않는다.

    **결과는 원본 프레임을 들고 나가지 않는다.** 오버레이가 필요한 호출자는
    PoseResult.load_frames()로 그때 다시 디코딩한다 — 그 사이 영상 파일이
    남아 있어야 한다(api_video의 임시 파일은 응답을 만들 때까지 산다).
    """
    import torch
    from transformers import (
        AutoProcessor,
        RTDetrForObjectDetection,
        VitPoseForPoseEstimation,
    )

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    frames, src_fps, sampled_fps = read_frames(
        video_path, target_fps, max_frames, max_seconds
    )

    det_processor = AutoProcessor.from_pretrained(PERSON_DETECTOR)
    detector = RTDetrForObjectDetection.from_pretrained(PERSON_DETECTOR).to(device).eval()
    pose_processor = AutoProcessor.from_pretrained(POSE_MODEL)
    pose_model = VitPoseForPoseEstimation.from_pretrained(POSE_MODEL).to(device).eval()

    all_kps: list[np.ndarray] = []
    # 프레임별 person 후보 수 — 사람이 없던 프레임도 (0, 0)으로 채운다.
    # 빠뜨리면 다중인원 비율의 분모가 어긋난다.
    cand_counts: list[tuple[int, int]] = []
    # 프레임마다 도구 검출 결과를 모은다. 사람이 없는 프레임에도 공은 있을 수
    # 있으므로 person 분기와 독립적으로 기록한다.
    obj_frames: list[dict[str, tuple[float, float, float]]] = []

    # 프레임별 자동 선택 결과와, 지정이 있을 때만 쓰는 후보 목록.
    auto_boxes: list[tuple[float, float, float, float] | None] = []
    candidates: list[list[tuple[float, float, float, float]]] = []

    try:
        # === 1차: 검출 ===
        #
        # 옛 구조는 프레임마다 검출과 포즈를 붙여서 했다. 대상 지정이 들어오면
        # 선택이 **프레임을 가로질러** 이어져야 하므로(찍은 프레임에서 앞뒤로
        # 전파한다) 검출을 먼저 다 끝내야 한다.
        #
        # 🔴 **RGB 프레임을 쌓아 두지 않는다.** 4K 300장이 약 7GB인데 사본을
        # 하나 더 들면 그대로 두 배다(미결 9번). 2차에서 다시 변환한다 —
        # cvtColor는 추론 앞에서 무시할 수 있는 비용이다.
        # 검출 결과도 통째로 들지 않고 **박스만** 뽑아 둔다.
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
            auto_boxes.append(_largest_person_box(detections))
            # 지정이 없으면 후보 목록을 만들지 않는다 — 쓰이지도 않는 것을
            # 프레임마다 쌓을 이유가 없다.
            candidates.append(
                _eligible_person_boxes(detections) if subject is not None else []
            )

        height, width = frames[0].shape[:2]
        subject_boxes, selection = select_subject_boxes(
            auto_boxes, candidates, subject, sampled_fps, (width, height)
        )

        # === 2차: 포즈 ===
        for frame, box in zip(frames, subject_boxes):
            if box is None:
                # 사람이 검출되지 않은 프레임은 신뢰도 0으로 채운다.
                # (프레임을 버리지 않는다 — 키포인트 인덱스 t가 곧 샘플링된
                #  프레임 인덱스 t여야 재디코딩한 프레임과 짝이 맞는다.)
                all_kps.append(np.zeros((17, 3)))
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
    finally:
        # 판정 모델을 올릴 VRAM을 비운다.
        del detector, pose_model
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    result = PoseResult(
        keypoints=np.stack(all_kps),
        source_fps=src_fps,
        sampled_fps=sampled_fps,
        # 프레임 대신 다시 얻는 방법을 넘긴다. 여기서 frames를 놓아 주므로
        # 판정 모델이 올라갈 때 원본 프레임이 메모리에 남지 않는다.
        video_path=str(video_path),
        target_fps=target_fps,
        max_frames=max_frames,
        max_seconds=max_seconds,
        objects=stack_object_tracks(obj_frames),
        candidate_counts=cand_counts,
        subject_boxes=subject_boxes,
        frame_size=(width, height),
        subject_selection=selection,
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
