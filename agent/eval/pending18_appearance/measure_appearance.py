#!/usr/bin/env python3
"""처방 (가) 외양 모델 — 이어가기가 갈아타는 것을 막는가 (미결 18번).

    uv run python eval/pending18_appearance/measure_appearance.py   # GPU 불필요

지금 이어가기는 **순수 IoU 탐욕 연결**이라 **크고 가만히 선 사람이 IoU
흡인원**이 된다. 여기에 닻 프레임의 **HSV 색 히스토그램**을 곱해 그 흡인을
줄이는 것이 처방 (가)다 (프론트 `personTrack.ts` 가 쓰는 방법).

합격선·상수·표본은 데이터를 보기 전에 `PREREGISTRATION.md` 에 박았다
(커밋 `19f248f`). **결과를 보고 바꾸지 않는다.**

🔴 **`src/` 를 고치지 않는다.** 조사 회차라 프로토타입은 여기 두고 production
은 import 만 한다 — `_iou`·`count_area_jumps`·`anchor_frame_for`·
`MIN_ANCHOR_IOU` 는 공유해서 규칙이 갈리지 않게 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from labeling.targets import load_candidates  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    MIN_ANCHOR_IOU,
    SubjectRequest,
    _iou,
    anchor_frame_for,
    count_area_jumps,
    read_frames,
    select_subject_boxes,
)

# 🔴 경로를 박지 않는다 — `eval/phaseA/paths.py` 가 정한다 (미결 14번).
from paths import external_root  # noqa: E402


# --- 사전 등록 상수 — 결과를 보고 바꾸지 않는다 ---------------------------
H_BINS, S_BINS = 32, 32
APP_FLOOR = 0.3

CLIPS = ROOT.parent / "clips"  # 아래 main 에서 실제 경로로 바꾼다
PERSON_THRESHOLD = 0.5  # `_largest_person_box`·`_eligible_person_boxes` 와 같은 값

# 미결 18번이 쓴 그 10건. **새로 고르지 않는다** — 고르면 표본이 결과를 만든다.
BOXES = {
    "3R1kvNrGJK0": ((0.492, 0.287, 0.083, 0.306), 3000.0),
    "Atzrde5uGcM": ((0.55, 0.20, 0.20, 0.42), 2002.0),
    "Fz16t9SrF3U": ((0.46, 0.16, 0.13, 0.50), 2000.0),
    "GS-PcxmaHmQ": ((0.30, 0.06, 0.26, 0.88), 2002.0),
    "IYFifBJ9lH8": ((0.44, 0.36, 0.17, 0.48), 2002.0),
    "O2GSaYqH8JY": ((0.30, 0.32, 0.12, 0.53), 2002.0),
    "ZMy0t-CSZiU": ((0.26, 0.13, 0.24, 0.78), 2002.0),
    "cDRi9AzrapA": ((0.24, 0.38, 0.28, 0.60), 2400.0),
    "sGKeqfxwq5E": ((0.30, 0.20, 0.13, 0.45), 2002.0),
    "xMIUw5mi3Eo": ((0.28, 0.28, 0.19, 0.60), 2002.0),
}

# 눈으로 확인해 둔 지금 상태 (미결 18번). 합격 판정의 기준선이다.
SWITCHING = {"3R1kvNrGJK0", "Fz16t9SrF3U", "sGKeqfxwq5E"}


def boxes_from_cache(clip: str):
    """캐시 후보 → (auto_boxes, candidates). production 의 두 규칙을 그대로 쓴다."""
    per_frame, wh, fps = load_candidates(clip)
    auto: list[tuple[float, float, float, float] | None] = []
    cands: list[list[tuple[float, float, float, float]]] = []
    for arr in per_frame:
        here: list[tuple[float, float, float, float]] = []
        best, best_area = None, 0.0
        for x1, y1, x2, y2, score in arr:
            if float(score) < PERSON_THRESHOLD:
                continue
            box = (float(x1), float(y1), float(x2 - x1), float(y2 - y1))
            here.append(box)
            area = box[2] * box[3]
            if area > best_area:
                best, best_area = box, area
        auto.append(best)
        cands.append(here)
    return auto, cands, wh, fps


def hist_of(frame: np.ndarray, box) -> np.ndarray | None:
    """박스 안 HSV 색 히스토그램. 너무 작으면 None."""
    h, w = frame.shape[:2]
    x, y, bw, bh = box
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(w, int(x + bw)), min(h, int(y + bh))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [H_BINS, S_BINS], [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def similarity(a: np.ndarray | None, b: np.ndarray | None) -> float:
    """0~1. 못 재면 1.0 — **모르는 것을 벌하지 않는다**(그러면 IoU 만으로 돈다)."""
    if a is None or b is None:
        return 1.0
    v = float(cv2.compareHist(a, b, cv2.HISTCMP_CORREL))
    return max(0.0, min(1.0, v))


def track_with_appearance(auto_boxes, candidates, frames, subject, fps, wh):
    """production `select_subject_boxes` 의 이어가기에 외양 항을 곱한 판.

    닻 고르기·끊김 처리는 production 과 **같은 규칙**이다. 다른 것은 이어갈
    후보를 고르는 점수 하나뿐이라 그 차이만 결과에 나온다.
    """
    n = len(auto_boxes)
    width, height = wh
    anchor, _offset, _clamped = anchor_frame_for(subject.at_ms, fps, n)
    x, y, bw, bh = subject.box
    pixel_box = (x * width, y * height, bw * width, bh * height)

    best_iou, best_box = 0.0, None
    for cand in candidates[anchor]:
        iou = _iou(pixel_box, cand)
        if iou > best_iou:
            best_iou, best_box = iou, cand
    if best_box is None or best_iou < MIN_ANCHOR_IOU:
        return auto_boxes, 0, 0.0  # 닻 실패 — production 과 같이 자동으로 떨어진다

    # 🔴 닻의 히스토그램을 끝까지 쓴다. 갱신하면 갈아탄 뒤의 외양을 학습해
    #    잘못된 대상에 고착된다 (사전 등록).
    anchor_hist = hist_of(frames[anchor], best_box) if anchor < len(frames) else None

    chosen: list[tuple[float, float, float, float] | None] = [None] * n
    chosen[anchor] = best_box
    breaks = 0

    def walk(order, seed):
        nonlocal breaks
        previous = seed
        for t in order:
            pick, pick_score = None, 0.0
            frame = frames[t] if t < len(frames) else None
            for cand in candidates[t]:
                iou = _iou(previous, cand)
                if iou <= 0.0:
                    continue
                app = 1.0
                if frame is not None:
                    app = similarity(anchor_hist, hist_of(frame, cand))
                score = iou * (APP_FLOOR + (1.0 - APP_FLOOR) * app)
                if score > pick_score:
                    pick, pick_score = cand, score
            if pick is None:
                breaks += 1
                chosen[t] = auto_boxes[t]
                if auto_boxes[t] is not None:
                    previous = auto_boxes[t]
                continue
            chosen[t] = pick
            previous = pick

    walk(range(anchor + 1, n), best_box)
    walk(range(anchor - 1, -1, -1), best_box)
    return chosen, breaks, best_iou


def differing(chosen, auto) -> int:
    return sum(1 for c, a in zip(chosen, auto) if c is not None and a is not None and c != a)


def main() -> None:
    clips_dir = external_root() / "clips"
    if not clips_dir.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {clips_dir}")

    print(f"{'clip':14s} {'상태':6s} │ {'점프(현)':>7s} {'점프(외양)':>9s} │ "
          f"{'갈림(현)':>8s} {'갈림(외양)':>10s} │ 판정")
    print("─" * 88)

    fixed = broke = kept = 0
    diverge_drop: list[str] = []
    rows = []

    for clip, (box, at_ms) in sorted(BOXES.items()):
        auto, cands, wh, fps = boxes_from_cache(clip)
        frames, _src_fps, _s = read_frames(clips_dir / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)

        base_boxes, base_sel = select_subject_boxes(auto, cands, subject, fps, wh)
        proto_boxes, _breaks, _iou0 = track_with_appearance(
            auto, cands, frames, subject, fps, wh)

        base_jumps = base_sel.area_jumps
        proto_jumps = count_area_jumps(proto_boxes)
        base_diff = differing(base_boxes, auto)
        proto_diff = differing(proto_boxes, auto)

        switching = clip in SWITCHING
        if switching:
            verdict = "✅ 점프 사라짐" if proto_jumps == 0 else "— 그대로"
            if proto_jumps == 0:
                fixed += 1
            if proto_diff < base_diff:
                diverge_drop.append(clip)
        else:
            if proto_jumps > 0:
                verdict = "🔴 깨끗하던 것이 깨졌다"
                broke += 1
            else:
                verdict = "✅ 유지"
                kept += 1

        rows.append((clip, switching, base_jumps, proto_jumps, base_diff, proto_diff))
        print(f"{clip:14s} {'갈아탐' if switching else '깨끗':6s} │ "
              f"{base_jumps:7d} {proto_jumps:9d} │ {base_diff:8d} {proto_diff:10d} │ {verdict}")

    # --- 사전 등록한 합격 기준 넷 ------------------------------------------
    print("\n" + "═" * 88)
    print("사전 등록 합격 기준 (결과를 보고 바꾸지 않는다)")
    print("═" * 88)

    # A: 자동 경로 — 지정이 없으면 production 은 auto_boxes 를 **그대로** 돌려준다.
    #    프로토타입은 그 갈래에 손대지 않는다. 그것을 실제로 확인한다.
    a_ok = True
    for clip in sorted(BOXES):
        auto, cands, wh, fps = boxes_from_cache(clip)
        got, sel = select_subject_boxes(auto, cands, None, fps, wh)
        if got is not auto or sel.source != "auto":
            a_ok = False
    print(f"  A 자동 경로 비트 동일 …… {'✅ 만족' if a_ok else '🔴 불만족'}"
          "   (지정 없으면 같은 객체를 그대로 반환 — B-6 재실행 없음)")

    b_ok = broke == 0
    print(f"  B 깨끗한 7건 유지 ……… {'✅ 만족' if b_ok else '🔴 불만족'}"
          f"   ({kept}/7 유지 · 깨진 것 {broke})")

    c_ok = fixed >= 2
    print(f"  C 갈아탄 3건 중 2건+ … {'✅ 만족' if c_ok else '🔴 불만족'}"
          f"   (점프 0 이 된 것 {fixed}/3)")

    d_ok = not diverge_drop
    print(f"  D 갈림이 줄지 않을 것 … {'✅ 만족' if d_ok else '🔴 불만족'}"
          + (f"   (준 것: {', '.join(diverge_drop)})" if diverge_drop else
             "   (자동 트랙으로 흡수돼 점프가 0이 되는 길을 막는 조건)"))

    # --- 왜 안 됐는가 — 불합격이면 기전을 밝힌다 -------------------------
    #
    # 🔴 「안 됐다」만 남기면 다음 사람이 같은 것을 다시 시도한다.
    print("\n" + "═" * 88)
    print("기전 — 점프가 난 프레임에 **고를 것이 몇 개나 있었나**")
    print("═" * 88)
    for clip in sorted(SWITCHING):
        box, at_ms = BOXES[clip]
        auto, cands, wh, fps = boxes_from_cache(clip)
        frames, _f, _s = read_frames(clips_dir / f"{clip}.mp4")
        anchor, _o, _c = anchor_frame_for(at_ms, fps, len(auto))
        W, H = wh
        pb = (box[0] * W, box[1] * H, box[2] * W, box[3] * H)
        seed = max(cands[anchor], key=lambda c: _iou(pb, c), default=None)
        if seed is None:
            continue
        ah = hist_of(frames[anchor], seed)
        prev, told = seed, False
        for t in range(anchor + 1, len(auto)):
            adm = [(_iou(prev, c), c) for c in cands[t] if _iou(prev, c) > 0]
            if not adm:
                print(f"  {clip:14s} f{t}: 겹치는 후보 0개 → 끊김 (가림 계열)")
                told = True
                break
            iou, pick = max(adm, key=lambda z: z[0])
            pa, qa = prev[2] * prev[3], pick[2] * pick[3]
            if qa > 2 * pa or pa > 2 * qa:
                app = similarity(ah, hist_of(frames[t], pick))
                print(f"  {clip:14s} f{t}: 넓이 {qa / pa:.1f}배 점프 · "
                      f"**겹치는 후보 {len(adm)}개** / 전체 {len(cands[t])}개 · "
                      f"고른 것 app {app:.2f}")
                told = True
                break
            prev = pick
        if not told:
            print(f"  {clip:14s} 점프 자리를 못 찾았다")

    print("\n🔴 겹치는 후보가 **1개뿐인 프레임**에서는 곱셈 가중치가 argmax 를")
    print("   바꿀 수 없다 — 무엇을 곱해도 유일한 후보가 이긴다. 처방 (가)를")
    print("   **재가중**으로 구현하는 한 이 실패는 원리적으로 안 고쳐진다.")

    print("\n" + "═" * 88)
    if a_ok and b_ok and c_ok and d_ok:
        print("판정: **합격** — 다음 회차에서 구현할 근거가 생겼다.")
        print("🔴 「갈아타기를 고쳤다」가 아니다 — 표본 10건이고 판독이 내 것이다.")
    else:
        print("판정: **불합격** — 이 설정의 외양 모델로는 부족하다.")
        print("🔴 「외양 모델은 안 된다」가 아니다 — 설정 하나를 재 본 것이다.")
    print("🔴 어느 쪽이든 이 회차는 `src/` 를 고치지 않는다.")


if __name__ == "__main__":
    main()
