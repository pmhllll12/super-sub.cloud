#!/usr/bin/env python3
"""미결 6번 — 스윙 측을 사람이 빠르게 판정할 판독 자료를 만든다.

**라벨을 만들지 않는다.** 사람이 보고 채울 자료만 낸다.

클립당 이미지 한 장이다. 자세 시퀀스 6칸 + 전체 프레임 1칸.

  uv run python eval/pending6_side/labeling/make_packet.py [--limit N] [--quality Q]

설계에서 정한 것들
------------------

**(1) 시점은 좌우 대칭인 활동량으로 고른다.**
10초 클립에서 스윙은 1초 남짓이라 균등 간격 6장은 동작을 통째로 놓친다.
그렇다고 "왼손목이 가장 많이 움직인 구간"으로 고르면 **판정 대상인 그
신호로 화면을 고르는 것**이라 앵커링이 된다. 그래서 양쪽 손목·발목 이동량의
**합**을 쓴다 — 좌우에 대칭이므로 *언제*를 고를 뿐 *어느 쪽*을 암시하지 않는다.

**(2) 스켈레톤을 그린다. 양쪽을 똑같이 그린다.**
원본만으로는 헐렁한 옷·역광에서 팔다리 구분이 느리다. 다만 자동 판별이 고른
쪽을 강조하면 그대로 앵커링이라, 좌우 선·점·글자를 **같은 색 같은 크기**로
그린다 (B-4 검수 패킷이 후보 상자를 전부 같은 색으로 그린 것과 같은 이유).

**(3) L/R을 관절에 직접 쓴다.**
화면 좌우와 인체 좌우가 다르고, 정면 구도에서는 뒤집힌다. 사람이 머릿속에서
변환하게 두면 느려지고 틀린다. **자세 추정 모델이 붙인 해부학적 좌우**를 손목과
발목에 글자로 얹는다 — 알고리즘의 답도 같은 좌표계라 그대로 대조된다.

**(4) 전체 프레임 한 칸을 함께 둔다.**
잘라낸 그림만 보면 **대상 선수를 잘못 골랐을 때 알 수 없다**(평가셋에 실제로
있다 — 공 줍는 코치를 잡은 클립). 자른 영역을 표시한 전체 프레임을 옆에 두어
사람이 그것을 잡아낼 수 있게 한다.

**(5) 자동 판별·마진·fps 갈림은 넣지 않는다.** `side_stats.py`가 낸 표에 있고,
그것은 라벨이 채워진 뒤에 본다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent.parent
sys.path.insert(0, str(AGENT / "src"))
sys.path.insert(0, str(AGENT / "eval" / "phaseA"))

from supersub_agent.features import (  # noqa: E402
    L_ANKLE, L_WRIST, R_ANKLE, R_WRIST,
)
from supersub_agent.pose import DEFAULT_TARGET_FPS, SKELETON, read_frames  # noqa: E402
from paths import cache_dir, require_external  # noqa: E402

PANELS = 6                # 자세 시퀀스 칸 수
PANEL_H = 420             # 칸 높이(px). 폭은 자른 영역 비율에 맞춘다
WINDOW_SEC = 1.4          # 활동 구간 길이
SMOOTH_SEC = 0.3          # 활동량 평활 창
MIN_CONF = 0.3            # 그릴 관절 신뢰도 하한
CROP_MARGIN = 0.35

# 좌우를 **똑같이** 그린다. 색으로 편을 가르지 않는다.
LINE_BGR = (90, 220, 90)
JOINT_BGR = (60, 60, 240)
TEXT_BGR = (255, 255, 255)
TEXT_EDGE = (0, 0, 0)

MARKED = {L_WRIST: "L", R_WRIST: "R", L_ANKLE: "L", R_ANKLE: "R"}


def activity(kps: np.ndarray, fps: float) -> np.ndarray:
    """좌우 대칭 활동량 — 양쪽 손목·발목 이동량의 합 (프레임당).

    한쪽만 보면 판정 대상인 신호로 화면을 고르게 된다. 합은 좌우를 바꿔도
    같은 값이므로 *언제*만 고른다.
    """
    xy = kps[:, :, :2]
    conf = kps[:, :, 2]
    total = np.zeros(len(kps))
    for j in (L_WRIST, R_WRIST, L_ANKLE, R_ANKLE):
        d = np.linalg.norm(np.diff(xy[:, j], axis=0), axis=1)
        ok = (conf[1:, j] >= MIN_CONF) & (conf[:-1, j] >= MIN_CONF)
        total[1:] += np.where(ok, d, 0.0)
    # 사람 크기로 정규화한다 — 원거리 클립과 근접 클립을 같은 기준으로 본다.
    scale = _body_scale(kps)
    if scale > 0:
        total /= scale
    w = max(1, int(round(SMOOTH_SEC * fps)))
    if w > 1:
        total = np.convolve(total, np.ones(w) / w, mode="same")
    return total


def _body_scale(kps: np.ndarray) -> float:
    """어깨~발목 정도의 대표 길이. 없으면 0."""
    valid = kps[kps[:, :, 2] >= MIN_CONF]
    if len(valid) < 4:
        return 0.0
    return float(np.percentile(np.abs(valid[:, 1] - np.median(valid[:, 1])), 90)) * 2 or 0.0


def pick_frames(kps: np.ndarray, fps: float, n: int = PANELS) -> list[int]:
    """활동이 가장 몰린 구간에서 균등하게 n장을 고른다."""
    T = len(kps)
    if T <= n:
        return list(range(T))
    act = activity(kps, fps)
    win = min(T, max(n, int(round(WINDOW_SEC * fps))))
    csum = np.concatenate([[0.0], np.cumsum(act)])
    sums = csum[win:] - csum[:-win]
    start = int(np.argmax(sums))
    idx = np.linspace(start, start + win - 1, n)
    return [int(round(v)) for v in idx]


def crop_box(kps: np.ndarray, frames: list[int], shape) -> tuple[int, int, int, int]:
    """고른 프레임 전체를 담는 하나의 자르기 영역 — 칸마다 달라지면 눈이 흔들린다."""
    h, w = shape[:2]
    pts = []
    for t in frames:
        v = kps[t][kps[t][:, 2] >= MIN_CONF][:, :2]
        if len(v):
            pts.append(v)
    if not pts:
        return 0, 0, w, h
    p = np.concatenate(pts)
    x1, y1 = p.min(axis=0)
    x2, y2 = p.max(axis=0)
    pad = CROP_MARGIN * max(x2 - x1, y2 - y1, 1.0)
    return (max(0, int(x1 - pad)), max(0, int(y1 - pad)),
            min(w, int(x2 + pad)), min(h, int(y2 + pad)))


def fit(img: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, float, tuple[int, int]]:
    """비율을 지키며 (w, h) 캔버스 가운데에 놓고 (그림, 배율, 배치 오프셋)을 준다.

    배율과 오프셋을 함께 돌려주는 이유: **선과 글자는 축소한 뒤에 그려야
    한다.** 원본에 그리고 줄이면 4K 클립에서 L/R 글자가 읽히지 않는 크기가
    된다 — 첫 판에서 실제로 그랬다.
    """
    w, h = size
    ih, iw = img.shape[:2]
    if ih == 0 or iw == 0:
        return np.zeros((h, w, 3), np.uint8), 1.0, (0, 0)
    s = min(w / iw, h / ih)
    r = cv2.resize(img, (max(1, int(iw * s)), max(1, int(ih * s))), interpolation=cv2.INTER_AREA)
    out = np.zeros((h, w, 3), np.uint8)
    x0 = (w - r.shape[1]) // 2
    y0 = (h - r.shape[0]) // 2
    out[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r
    return out, s, (x0, y0)


def draw_pose(img: np.ndarray, kps: np.ndarray, crop_xy=(0, 0),
              scale: float = 1.0, place=(0, 0), text: bool = True) -> None:
    """스켈레톤과 L/R 글자. **좌우를 구분해 강조하지 않는다.**

    캔버스 좌표 = (원본 − 자른 좌상단) × 배율 + 배치 오프셋.
    """
    cx, cy = crop_xy
    px, py = place

    def pt(i):
        return (int((kps[i, 0] - cx) * scale + px), int((kps[i, 1] - cy) * scale + py))

    thick = 2
    for a, b in SKELETON:
        if kps[a, 2] >= MIN_CONF and kps[b, 2] >= MIN_CONF:
            cv2.line(img, pt(a), pt(b), LINE_BGR, thick, cv2.LINE_AA)
    for i in range(len(kps)):
        if kps[i, 2] >= MIN_CONF:
            cv2.circle(img, pt(i), 3, JOINT_BGR, -1, cv2.LINE_AA)

    if not text:
        return
    # 칸 크기에 맞춘 고정 크기 — 클립 해상도와 무관하게 같게 읽힌다.
    #
    # **L은 왼쪽 위, R은 오른쪽 아래에 붙인다.** 야구 타격은 두 손으로 잡아
    # 양 손목이 겹치는데, 같은 자리에 쓰면 "LR"로 뭉쳐 둘 다 못 읽는다.
    # 클립 내용과 무관한 고정 규칙이므로 어느 쪽을 유도하지 않는다.
    for j, ch in MARKED.items():
        if kps[j, 2] < MIN_CONF:
            continue
        x, y = pt(j)
        org = (x - 30, y - 9) if ch == "L" else (x + 11, y + 26)
        cv2.putText(img, ch, org, cv2.FONT_HERSHEY_DUPLEX, 0.9, TEXT_EDGE, 5, cv2.LINE_AA)
        cv2.putText(img, ch, org, cv2.FONT_HERSHEY_DUPLEX, 0.9, TEXT_BGR, 2, cv2.LINE_AA)


def label(img: np.ndarray, text: str, org=(8, 22), fs: float = 0.5) -> None:
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, fs, TEXT_EDGE, 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, fs, TEXT_BGR, 1, cv2.LINE_AA)


def build_sheet(cid: str, kps: np.ndarray, frames_all: list[np.ndarray],
                fps: float) -> np.ndarray:
    idx = pick_frames(kps, fps)
    idx = [t for t in idx if t < len(frames_all)]
    x1, y1, x2, y2 = crop_box(kps, idx, frames_all[idx[0]].shape)

    # 칸 비율을 자른 영역에 맞춘다 — 정사각 칸에 세로로 선 사람을 넣으면
    # 화면의 절반이 검은 여백이 되고 그만큼 인물이 작아진다.
    cw, ch = max(1, x2 - x1), max(1, y2 - y1)
    pw = int(np.clip(round(PANEL_H * cw / ch), 240, 620))
    cols, rows = 3, 2

    grid = np.zeros((rows * PANEL_H, cols * pw, 3), np.uint8)
    for i, t in enumerate(idx[:cols * rows]):
        panel, s, place = fit(frames_all[t][y1:y2, x1:x2], (pw, PANEL_H))
        draw_pose(panel, kps[t], (x1, y1), s, place)
        label(panel, f"{i + 1}   t={t / fps:.2f}s")
        r, c = divmod(i, cols)
        grid[r * PANEL_H:(r + 1) * PANEL_H, c * pw:(c + 1) * pw] = panel

    # 전체 프레임 — 자른 영역을 표시해 "대상 선수를 잘못 골랐는지" 보이게 한다.
    mid = idx[len(idx) // 2]
    fh, fw = frames_all[mid].shape[:2]
    ctx_w = int(np.clip(round(rows * PANEL_H * fw / fh), 320, 720))
    ctx, s, place = fit(frames_all[mid], (ctx_w, rows * PANEL_H))
    draw_pose(ctx, kps[mid], (0, 0), s, place, text=False)
    cv2.rectangle(ctx,
                  (int(x1 * s + place[0]), int(y1 * s + place[1])),
                  (int(x2 * s + place[0]), int(y2 * s + place[1])),
                  (255, 255, 255), 2)
    label(ctx, "전체 화면 (흰 테두리 = 왼쪽 6칸의 범위)")

    sheet = np.hstack([grid, ctx])
    head = np.zeros((44, sheet.shape[1], 3), np.uint8)
    label(head, f"{cid}    L/R = 자세추정 모델의 해부학적 좌우 (화면 좌우가 아님)",
          org=(10, 29), fs=0.62)
    return np.vstack([head, sheet])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "review_packet" / "images")
    ap.add_argument("--limit", type=int, default=0, help="앞 N개만 (확인용)")
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--only", default=None, help="클립 하나만")
    args = ap.parse_args()

    clips_dir = require_external("clips/*.mp4") / "clips"
    c30 = cache_dir(30)
    clips = sorted(p.stem for p in c30.glob("*.npz") if ".ERROR" not in p.name)
    if args.only:
        clips = [c for c in clips if c == args.only]
    if args.limit:
        clips = clips[:args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    total = 0
    for i, cid in enumerate(clips, 1):
        mp4 = clips_dir / f"{cid}.mp4"
        if not mp4.exists():
            print(f"  건너뜀 {cid}: 원본 클립이 없다", file=sys.stderr)
            continue
        d = np.load(c30 / f"{cid}.npz", allow_pickle=True)
        kps = d["keypoints"]
        frames, _, sampled = read_frames(mp4, DEFAULT_TARGET_FPS)
        n = min(len(frames), len(kps))
        sheet = build_sheet(cid, kps[:n], frames[:n], sampled)
        path = args.out / f"{cid}.jpg"
        cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
        size = path.stat().st_size
        total += size
        print(f"[{i:2d}/{len(clips)}] {cid:16s} {sheet.shape[1]}x{sheet.shape[0]}  {size/1024:6.0f}KB")
    print(f"\n합계 {total/1024/1024:.1f}MB · {len(clips)}장 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
