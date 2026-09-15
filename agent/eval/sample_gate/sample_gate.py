"""표본 관문 — **회차를 열기 전에** 이 표본에 그 현상이 있는지 먼저 묻는다.

🔴 **왜 있는가.** 미결 `ho` 18번 11회차가 사전 등록·계기·판정을 다 갖추고
돌았는데 **주 층이 19편에서 1프레임**이라 분모가 0편으로 끝났다. 표본에
**후보가 2명 이상인 프레임이 8%** 뿐이었고, 그 값은 **검출 한 번(GPU 100초)**
이면 나왔다. **회차를 통째로 열기 전에 물었어야 할 질문이다.**

그래서 로드맵 5절의 계기 검사 셋 중 세 번째 — **「표본에 그 현상이 있기는
한가」** — 를 한 줄로 돌릴 수 있게 만든 것이 이 스크립트다.

🔴 **판정 회차가 아니다.** 가설을 재지 않고 사전 등록도 없다. 여기 나오는
숫자는 **회차를 열지 말지**를 정하는 데 쓰고, 열기로 하면 그 회차의 사전
등록에 이 값을 적는다.

🔴 **`src/` 를 고치지 않는다** — production 을 import 만 한다. ViTPose 는
안 돌린다(검출만).

    cd agent && uv run python eval/sample_gate/sample_gate.py --sample soccer
    cd agent && uv run python eval/sample_gate/sample_gate.py --sample phasea --limit 10
    cd agent && uv run python eval/sample_gate/sample_gate.py --sample soccernet
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.pose import (  # noqa: E402
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    PERSON_ELIGIBLE_THRESHOLD,
    _eligible_person_boxes,
    _load_detector,
    _tracked_centers,
    read_frames_ex,
    stack_object_tracks,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent

# ── 🔴 바(bar)는 **SoccerNet 숫자를 보기 전에** 정했다 (2026.09.14). ────────
#    결과를 보고 내리면 관문이 아무것도 안 막는다.
MULTI_BAR = 0.10        # 후보 2명 이상인 프레임이 이 미만이면 **표본을 바꾼다**
NEAR = 0.25             # 키높이 — 18번 11회차와 같은 값
MIN_NEAR_FRAMES = 5     # 클립이 「주 층에 든다」고 볼 최소 프레임
MAX_BALL_SPEED_H = 1.0  # 45번 3회차 4.0 어깨너비/프레임의 단위 변환

SAMPLES = {
    "soccer":    (lambda: paths.soccer_clips_root(), "*.avi",
                  "축구 19편 — 1인 훈련 영상 (18번 11회차가 쓴 것)"),
    "soccernet": (lambda: paths.soccernet_clips_root(), "*.mp4",
                  "SoccerNet 방송 클립 — 다인 후보 (미결 46번)"),
    "phasea":    (lambda: paths.require_external("clips/") / "clips", "*.mp4",
                  "phaseA 골든셋 39편 — 야구. 🔴 **양성 대조군**이다"),
}


def gate_by_speed(ball: np.ndarray, scale: float) -> np.ndarray:
    """45번 3회차의 규칙 — 물리적으로 닿을 수 없는 위치는 미검출로 본다."""
    out = ball.copy()
    last_t = None
    for t in range(len(out)):
        if out[t, 2] <= 0:
            continue
        if last_t is None:
            last_t = t
            continue
        step = (np.hypot(*(out[t, :2] - out[last_t, :2])) / scale) / (t - last_t)
        if step > MAX_BALL_SPEED_H:
            out[t, 2] = 0.0
        else:
            last_t = t
    return out


def probe_clip(clip: Path, det_pair, device: str) -> dict:
    """검출 한 번. 관문 숫자 셋만 낸다."""
    import torch

    det_processor, detector = det_pair
    read = read_frames_ex(clip, DEFAULT_TARGET_FPS, None, DEFAULT_MAX_SECONDS)

    counts, boxes_per_frame, obj_frames = [], [], []
    for frame in read.frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inp = det_processor(images=rgb, return_tensors="pt").to(device)
        with torch.inference_mode():
            out = detector(**inp)
        det = det_processor.post_process_object_detection(
            out, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3
        )[0]
        boxes = _eligible_person_boxes(det)
        boxes_per_frame.append(boxes)
        counts.append(len(boxes))
        obj_frames.append(_tracked_centers(det))

    n = len(read.frames)
    heights = [b[3] for f in boxes_per_frame for b in f]
    H = float(statistics.median(heights)) if heights else 0.0

    ball = stack_object_tracks(obj_frames).get("sports_ball")
    ball_seen = 0
    near_multi = 0
    if ball is not None and H > 0:
        ball = gate_by_speed(ball, H)
        for t in range(n):
            if ball[t, 2] <= 0:
                continue
            ball_seen += 1
            if len(boxes_per_frame[t]) < 2:
                continue
            d = min(np.hypot(b[0] + b[2] / 2 - ball[t, 0], b[1] + b[3] - ball[t, 1]) / H
                    for b in boxes_per_frame[t])
            if d <= NEAR:
                near_multi += 1

    return {
        "clip": clip.name,
        "frames": n,
        "size": f"{read.frames[0].shape[1]}x{read.frames[0].shape[0]}" if n else "?",
        "person_height_px": round(H, 1),
        "multi_frames": sum(c >= 2 for c in counts),
        "cand_median": statistics.median(counts) if counts else 0,
        "cand_max": max(counts) if counts else 0,
        "ball_frames": ball_seen,
        "near_multi_frames": near_multi,
    }


def main() -> None:
    import torch

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", required=True, choices=sorted(SAMPLES))
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N 편만 (0=전부)")
    args = ap.parse_args()

    root_fn, glob, note = SAMPLES[args.sample]
    root = root_fn()
    clips = sorted(root.rglob(glob))
    if args.limit:
        clips = clips[: args.limit]
    if not clips:
        print(f"🔴 클립이 없다: {root}\n   {note}")
        raise SystemExit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"표본 `{args.sample}` — {note}")
    print(f"{root} · {len(clips)}편 · device={device} · "
          f"eligible≥{PERSON_ELIGIBLE_THRESHOLD}\n")

    det_pair = _load_detector(device)
    rows = []
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            r = probe_clip(clip, det_pair, device)
        except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 관문은 돈다
            print(f"  [{i}/{len(clips)}] {clip.name[:40]:40s} ⚠️ {type(exc).__name__}")
            continue
        rows.append(r)
        print(f"  [{i}/{len(clips)}] {clip.name[:40]:40s} "
              f"{r['size']:>9s} {r['frames']:3d}f · 사람 중앙 {r['cand_median']:.0f}"
              f"/최대 {r['cand_max']:2d} · 다인 {r['multi_frames']:3d}f · "
              f"공 {r['ball_frames']:3d}f · 발치다인 {r['near_multi_frames']:2d}f "
              f"({time.time()-t0:.1f}초)")

    (HERE / f"gate_{args.sample}.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(r["frames"] for r in rows)
    multi = sum(r["multi_frames"] for r in rows)
    ball = sum(r["ball_frames"] for r in rows)
    near = sum(r["near_multi_frames"] for r in rows)
    ok_clips = [r for r in rows if r["near_multi_frames"] >= MIN_NEAR_FRAMES]

    print("\n" + "=" * 72)
    print(f"클립 {len(rows)}편 · 프레임 {total}")
    print(f"  ⑴ 다인률   (후보 2명 이상)        : {multi/total:.0%}  ({multi}/{total})")
    print(f"  ⑵ 공 검출률                        : {ball/total:.0%}  ({ball}/{total})")
    print(f"  ⑶ 발치+다인 (18번 11회차의 주 층)  : {near/total:.1%} ({near}/{total})")
    print(f"      그 층에 {MIN_NEAR_FRAMES}프레임 이상인 클립 : "
          f"{len(ok_clips)}/{len(rows)}")
    heights = [r["person_height_px"] for r in rows if r["person_height_px"]]
    if heights:
        print(f"  (참고) 사람 박스 높이 중앙값       : "
              f"{statistics.median(heights):.0f}px "
              f"· 범위 {min(heights):.0f}~{max(heights):.0f}")

    print(f"\n🔴 관문 (바 {MULTI_BAR:.0%} 는 결과를 보기 전에 정했다)")
    if multi / total < MULTI_BAR:
        print(f"   ❌ 다인률 {multi/total:.0%} < {MULTI_BAR:.0%} — "
              f"**「여러 명 중 고르기」 회차를 이 표본으로 열지 않는다.**")
    else:
        print(f"   ✅ 다인률 {multi/total:.0%} ≥ {MULTI_BAR:.0%} — "
              f"「여러 명 중 고르기」를 물을 수 있다.")
    if not ok_clips:
        print(f"   ❌ 발치+다인 층에 {MIN_NEAR_FRAMES}프레임 이상인 클립이 "
              f"**0편** — 공 근접 축은 이 표본에서 안 선다.")
    else:
        print(f"   ✅ 공 근접 축이 설 클립 {len(ok_clips)}편.")
    print("\n🔴 이 숫자는 **표본의 성질**이지 우리 알고리즘의 성능이 아니다.")


if __name__ == "__main__":
    main()
