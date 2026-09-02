"""Phase B-0 공용 모듈 — 라벨 대상 프레임 결정과 후보 적재.

이 디렉터리의 도구는 전부 오프라인이다. production 저장소를 읽지도 쓰지도 않는다.
입력은 Phase A가 남긴 /mnt/d/supersub-phaseA/candidates/*.npz 뿐이다.

npz 구조 (Phase A candidates.py가 저장한 것):
    frame_wh     (2,)      [W, H]
    sampled_fps  ()        실효 샘플링 fps
    n            (T,)      프레임별 person 후보 수
    boxes        (sum(n),5) [x1, y1, x2, y2, score] — 프레임 순서로 이어 붙임

**box_index의 정의**: 해당 프레임의 후보 배열에서의 위치다. 이 배열은 RT-DETR
post_process(threshold=0.3)가 낸 person 검출 **전부**를 저장 순서 그대로 담는다.
production `_largest_person_box`는 score>=0.5만 보지만, 타자가 0.3~0.5 구간에
잡히는 프레임이 있을 수 있어 라벨은 더 넓은 쪽을 대상으로 한다. 좁게 잡으면
"정답이 후보에 없다"와 "라벨러가 못 찾았다"가 섞인다.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/d/supersub-phaseA")
CAND = ROOT / "candidates"
WORK = ROOT / "labeling"
RENDERS = WORK / "renders"
LABELS = WORK / "labels.json"

# 라벨을 붙일 클립 내 상대 위치. 순서를 바꾸지 않는다 — 저장된 라벨의 ratio와 대응한다.
RATIOS = (0.20, 0.50, 0.80)

# ---------------------------------------------------------------- 프레임 좌표계
#
# **labels.json의 `frame`은 target_fps=15로 뽑은 샘플 인덱스다.** 물리 시각이
# 아니다. `ratio`가 키이고 `frame`은 그때 유도된 파생값이라, target_fps가 바뀌면
# 같은 `frame` 값이 **다른 순간**을 가리킨다.
#
# read_frames(pose.py)의 샘플링 규칙:
#
#     step = max(1, round(src_fps / target_fps))
#     샘플 인덱스 i  ↔  원본 프레임 i * step
#
# 순차 디코딩이고 프레임을 버리기만 하므로, 같은 원본 인덱스는 target_fps와
# 무관하게 **같은 픽셀**이다. 따라서 라벨은 원본 프레임을 경유해 옮기면 된다.
#
#     원본 = frame_15 * step(src, 15)
#     frame_now = 원본 / step(src, target_fps)
#            = frame_15 * step(src, 15) / step(src, target_fps)
#
# target_fps=15면 두 step이 같아 **항등**이다.
#
# ratio로 다시 유도하면 안 된다 — frame_at의 반올림이 n_frames에 걸려 있어
# 이 데이터셋 117개 중 **42개가 원본 기준 1프레임씩 어긋난다**(예: 0Fet8TyoNR4
# ratio 0.8에서 원본 182 대 183). 라벨은 특정 박스를 가리키므로 1프레임도 틀리면
# 다른 사람을 가리킬 수 있다.
LABEL_TARGET_FPS = 15

# 클립별 원본 fps. read_frames가 step 계산에 쓰는 값이라 환산에 반드시 필요하다.
CLIP_SPECS = Path(__file__).resolve().parent.parent / "clip_specs.csv"


def sampling_step(src_fps: float, target_fps: int) -> int:
    """read_frames와 **같은** 규칙. 여기서 갈라지면 라벨이 조용히 어긋난다."""
    return max(1, round(src_fps / target_fps))


# read_frames의 max_frames 기본값과 같아야 한다. 여기서 갈라지면 긴 클립의
# 15fps 격자 길이를 잘못 잡아 라벨 프레임이 어긋난다.
MAX_FRAMES = 300


def clip_specs() -> dict[str, dict]:
    """clip_id → {"fps": 원본 fps, "nframes": 원본 총 프레임}."""
    with open(CLIP_SPECS, newline="") as fh:
        return {r["clip_id"]: {"fps": float(r["fps"]), "nframes": int(r["nframes"])}
                for r in csv.DictReader(fh)}


def sampled_length(nframes_src: int, src_fps: float, target_fps: int) -> int:
    """target_fps로 뽑았을 때의 샘플 수. read_frames의 루프와 같은 값이다.

    39클립 전수 대조로 실제 candidates npz의 길이와 일치함을 확인했다.
    """
    return min(MAX_FRAMES, math.ceil(nframes_src / sampling_step(src_fps, target_fps)))


def remap_label_frame(label_frame: int, src_fps: float, target_fps: int) -> int:
    """labels.json의 frame(15fps 샘플 인덱스)을 target_fps의 샘플 인덱스로.

    target_fps == LABEL_TARGET_FPS 이면 항등이다.

    step 배수가 정수가 아니면 원본 프레임이 새 격자에 **없다**는 뜻이다. 이
    데이터셋에서는 발생하지 않지만(39클립 전부 배수 2.0 또는 1.0), 조용히
    반올림해 다른 프레임을 가리키게 두면 안 되므로 막는다.
    """
    step_label = sampling_step(src_fps, LABEL_TARGET_FPS)
    step_now = sampling_step(src_fps, target_fps)
    source_index = label_frame * step_label
    if source_index % step_now:
        raise ValueError(
            f"원본 프레임 {source_index}가 target_fps={target_fps}의 격자에 없다 "
            f"(step {step_label}→{step_now}). 라벨을 다시 붙여야 한다."
        )
    return source_index // step_now


def frame_at(n_frames: int, ratio: float) -> int:
    """클립 길이와 비율로 프레임 인덱스를 정한다.

    **반올림 규칙은 round-half-up으로 고정한다.** 파이썬 내장 round()는 짝수
    반올림(banker's rounding)이라 0.5에서 결과가 값에 따라 갈린다 — 라벨과
    평가 스크립트가 같은 프레임을 가리켜야 하므로 규칙을 코드에 박아 둔다.

        frame = floor((n_frames - 1) * ratio + 0.5)
    """
    if n_frames < 1:
        raise ValueError(f"프레임 수가 0이다: {n_frames}")
    return int(math.floor((n_frames - 1) * ratio + 0.5))


def load_candidates(clip_id: str) -> tuple[list[np.ndarray], tuple[int, int], float]:
    """(프레임별 후보 배열, (W, H), sampled_fps).

    후보 배열은 (k, 5) — [x1, y1, x2, y2, score]. 후보가 없는 프레임은 (0, 5).
    """
    path = CAND / f"{clip_id}.npz"
    if not path.exists():
        raise FileNotFoundError(f"후보 캐시가 없다: {path}")
    d = np.load(path)
    counts = d["n"]
    boxes = d["boxes"]
    out: list[np.ndarray] = []
    cursor = 0
    for k in counts:
        k = int(k)
        out.append(boxes[cursor : cursor + k])
        cursor += k
    if cursor != len(boxes):
        raise ValueError(f"{clip_id}: n의 합 {cursor}가 boxes 길이 {len(boxes)}와 다르다")
    wh = (int(d["frame_wh"][0]), int(d["frame_wh"][1]))
    return out, wh, float(d["sampled_fps"])


def clip_ids() -> list[str]:
    """후보 캐시가 있는 클립 id 목록 (정렬 고정)."""
    return sorted(p.stem for p in CAND.glob("*.npz"))


def enumerate_targets(target_fps: int = LABEL_TARGET_FPS) -> list[dict]:
    """라벨 대상 117개를 결정론적으로 만든다.

    반환 순서가 곧 라벨링 순서이고, 평가 스크립트도 같은 순서를 재현한다.

    **대상은 물리 프레임으로 고정된다.** ratio는 LABEL_TARGET_FPS 격자에서 한
    번만 쓰이고, 거기서 나온 프레임을 현재 target_fps 격자로 환산한다. 현재
    격자에서 ratio를 다시 계산하지 않는다 — 그러면 반올림 때문에 저장된 라벨과
    다른 순간을 가리킨다(이 데이터셋 117개 중 42개).

    target_fps == LABEL_TARGET_FPS 이면 환산이 항등이라 이전 동작과 같다.
    """
    specs = clip_specs()
    targets: list[dict] = []
    for cid in clip_ids():
        per_frame, _, _ = load_candidates(cid)
        n_frames = len(per_frame)
        spec = specs[cid]
        # 라벨이 붙은 격자의 길이. 현재 npz가 어느 fps로 뽑혔든 이 값은 같다.
        n_label = sampled_length(spec["nframes"], spec["fps"], LABEL_TARGET_FPS)
        for ratio in RATIOS:
            label_frame = frame_at(n_label, ratio)
            t = remap_label_frame(label_frame, spec["fps"], target_fps)
            if not 0 <= t < n_frames:
                raise ValueError(
                    f"{cid}: 환산 프레임 {t}가 후보 캐시 범위(0~{n_frames - 1}) 밖이다. "
                    f"라벨 격자 {n_label}프레임, target_fps={target_fps}."
                )
            targets.append(
                {
                    "clip_id": cid,
                    "frame": t,
                    "ratio": ratio,
                    "n_candidates": int(len(per_frame[t])),
                    "n_frames": n_frames,
                    "label_frame": label_frame,
                    "source_frame": label_frame * sampling_step(spec["fps"], LABEL_TARGET_FPS),
                }
            )
    return targets


def target_key(clip_id: str, ratio: float) -> str:
    """라벨 파일에서 대상을 식별하는 키. ratio는 소수 2자리로 고정한다."""
    return f"{clip_id}@{ratio:.2f}"


if __name__ == "__main__":
    ts = enumerate_targets()
    clips = {t["clip_id"] for t in ts}
    print(f"clips: {len(clips)}")
    print(f"targets: {len(ts)}")
    print(f"후보 0개인 대상: {sum(1 for t in ts if t['n_candidates'] == 0)}")
    print(f"후보 1개인 대상: {sum(1 for t in ts if t['n_candidates'] == 1)}")
    print(f"후보 2개 이상인 대상: {sum(1 for t in ts if t['n_candidates'] >= 2)}")
    print(f"후보 수 최대: {max(t['n_candidates'] for t in ts)}")
