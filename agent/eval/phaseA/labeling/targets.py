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


def enumerate_targets() -> list[dict]:
    """라벨 대상 117개를 결정론적으로 만든다.

    반환 순서가 곧 라벨링 순서이고, 평가 스크립트도 같은 순서를 재현한다.
    """
    targets: list[dict] = []
    for cid in clip_ids():
        per_frame, _, _ = load_candidates(cid)
        n_frames = len(per_frame)
        for ratio in RATIOS:
            t = frame_at(n_frames, ratio)
            targets.append(
                {
                    "clip_id": cid,
                    "frame": t,
                    "ratio": ratio,
                    "n_candidates": int(len(per_frame[t])),
                    "n_frames": n_frames,
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
