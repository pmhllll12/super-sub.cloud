"""공만으로 이벤트를 찾는다 — 2회차 (미결 `ho` 45번 ㉲-a).

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `ef6b528`)을 먼저 읽는다.**
상수와 합격선은 이 파일을 쓰기 전에 굳혔고 결과를 보고 고치지 않는다.

🔴 **`src/` 를 한 줄도 안 고친다** — production 은 import 만 한다.

🔴 **`normalize_track` 을 안 쓴다.** 그것은 프레임마다 다른 골반 중심을 빼므로
속도에 **선수의 이동이 섞인다.** 여기서는 `normalization_params()` 의
`scale`(클립당 상수)로 **나누기만** 한다.

공 궤적을 `ball_tracks.npz` 로 남긴다 — 다음 회차가 GPU 없이 다시 볼 수 있게.

    cd agent && uv run python eval/pending45_ball_events/measure_ball_events.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.features import normalization_params  # noqa: E402
from supersub_agent.pose import extract_keypoints  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
MIN_ACCEL = 1.0            # 어깨너비 / 프레임²
MIN_GAP = 8                # 프레임 (1회차와 같은 값)
MIN_BALL_COVERAGE = 0.30


def ball_accel(ball: np.ndarray, scale: float) -> np.ndarray:
    """프레임별 |속도 변화| (어깨너비/프레임²). 잴 수 없으면 NaN.

    🔴 **평행이동을 빼지 않는다** — 스케일로 나누기만 한다. 골반 중심을 빼면
    선수가 뛸 때 공이 움직인 것이 된다.

    🔴 **연속 세 프레임에 공이 다 있어야** 가속을 낸다. 끊긴 구간을 이어
    붙이면 없는 가속을 지어낸다.
    """
    p = ball[:, :2] / scale
    seen = ball[:, 2] > 0
    n = len(ball)
    accel = np.full(n, np.nan)
    for t in range(1, n - 1):
        if not (seen[t - 1] and seen[t] and seen[t + 1]):
            continue
        v_prev = p[t] - p[t - 1]
        v_next = p[t + 1] - p[t]
        accel[t] = float(np.hypot(*(v_next - v_prev)))
    return accel


def find_events(accel: np.ndarray) -> list[int]:
    """`accel` 의 국소 최대점 중 이벤트로 볼 것들 (사전 등록 규칙 그대로)."""
    cand: list[int] = []
    for t in range(len(accel)):
        a = accel[t]
        if not np.isfinite(a) or a < MIN_ACCEL:
            continue
        prev = accel[t - 1] if t > 0 and np.isfinite(accel[t - 1]) else -np.inf
        nxt = accel[t + 1] if t + 1 < len(accel) and np.isfinite(accel[t + 1]) else -np.inf
        if a >= prev and a >= nxt:
            cand.append(t)
    kept: list[int] = []
    for t in sorted(cand, key=lambda i: -accel[i]):   # 강한 것부터
        if all(abs(t - k) >= MIN_GAP for k in kept):
            kept.append(t)
    return sorted(kept)


def main() -> None:
    clips = sorted(paths.soccer_clips_root().rglob("*.avi"))
    print(f"축구 세트피스 {len(clips)}편 · MIN_ACCEL={MIN_ACCEL} "
          f"MIN_GAP={MIN_GAP}\n")

    rows, tracks = [], {}
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            pose = extract_keypoints(clip, observe=False)
            ball = pose.objects.get("sports_ball")
            _, scale = normalization_params(pose.keypoints)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} ⚠️ {type(exc).__name__}")
            rows.append({"clip": clip.name, "error": repr(exc)})
            continue

        if ball is None:
            rows.append({"clip": clip.name, "ball_coverage": 0.0,
                         "skipped": "공 궤적 없음"})
            print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} 공 없음")
            continue

        tracks[clip.name] = ball
        coverage = float((ball[:, 2] > 0).mean())
        accel = ball_accel(ball, scale)
        events = find_events(accel)

        # 사후 관찰용 — 이벤트 직전 공 속도. 정지한 공이 급가속하면 진짜 킥일
        # 가능성이 크다. 🔴 판정에 안 쓴다 (사전 등록 「미리 아는 오염원」).
        p = ball[:, :2] / scale
        speed_before = []
        for t in events:
            if t >= 1 and ball[t - 1, 2] > 0 and ball[t, 2] > 0:
                speed_before.append(round(float(np.hypot(*(p[t] - p[t - 1]))), 3))
            else:
                speed_before.append(None)

        rows.append({
            "clip": clip.name, "frames": len(ball),
            "ball_coverage": round(coverage, 3),
            "events": events, "n_events": len(events),
            "accel_at_events": [round(float(accel[t]), 3) for t in events],
            "speed_before_events": speed_before,
            "accel_max": (round(float(np.nanmax(accel)), 3)
                          if np.isfinite(accel).any() else None),
            "seconds": round(time.time() - t0, 1),
        })
        print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} "
              f"이벤트 {len(events):2d} @{events} · 공커버 {coverage:.0%} · "
              f"최대가속 {rows[-1]['accel_max']}  ({rows[-1]['seconds']}초)")

    (HERE / "events_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    if tracks:
        # 🔴 다음 회차가 GPU 없이 다시 보게 남긴다.
        np.savez_compressed(HERE / "ball_tracks.npz", **tracks)

    ok = [r for r in rows if r.get("ball_coverage", 0) >= MIN_BALL_COVERAGE
          and "error" not in r and "skipped" not in r]
    dropped = [r for r in rows if r not in ok]

    print("\n" + "=" * 66)
    print(f"분모 {len(ok)}/{len(clips)} 편 (뺀 것 {len(dropped)}편)")
    if not ok:
        print("🔴 분모가 비었다 — 판정할 수 없다")
        return

    counts = [r["n_events"] for r in ok]
    found = sum(1 for c in counts if c >= 1) / len(counts)
    not_noisy = sum(1 for c in counts if c <= 2) / len(counts)

    print(f"이벤트 수: 중앙값 {statistics.median(counts)} · 분포 {sorted(counts)}")
    print("\n── 사전 등록 판정")
    print(f"  A 1개 이상 찾음 ≥80%   : {found:.0%} {'✅' if found >= 0.8 else '🔴'}")
    print(f"  B 2개 이하     ≥80%   : {not_noisy:.0%} {'✅' if not_noisy >= 0.8 else '🔴'}")
    print("  C production 무수정    : ✅ (import 만 한다)")
    print(f"  D 뺀 클립              : {len(dropped)}편 "
          f"{[r['clip'] for r in dropped] or ''}")

    print("\n── 사후 관찰 (판정에 안 쓴다)")
    still = [s for r in ok for s in r["speed_before_events"]
             if s is not None and s < 0.3]
    allsp = [s for r in ok for s in r["speed_before_events"] if s is not None]
    if allsp:
        print(f"  이벤트 직전 공이 거의 정지(<0.3 어깨너비/프레임): "
              f"{len(still)}/{len(allsp)}")
        print("  🔴 세트피스는 정지한 공을 차므로 이 비율이 높아야 진짜 킥에")
        print("     가깝다. 낮으면 카메라 팬 같은 오염을 의심한다.")


if __name__ == "__main__":
    main()
