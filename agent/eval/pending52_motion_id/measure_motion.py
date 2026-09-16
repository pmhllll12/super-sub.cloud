"""영상만 보고 슛인가 패스인가 — 1회차 측정 (미결 `ho` 52번).

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `d82550a` + 정정 `ff817d5`)을 먼저
읽는다.** 상수와 합격선은 이 파일을 쓰기 전에 굳혔고 결과를 보고 고치지 않는다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. production 은 **import 만** 하고
이 회차 전용 규칙(표 세기)만 여기 둔다.

    cd agent && uv run python eval/pending52_motion_id/measure_motion.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    LIMB_CHAINS,
    L_ANKLE,
    L_KNEE,
    R_ANKLE,
    chain_series,
    extract_features,
    identify_legs,
    normalize,
    normalize_track,
    segment_phases,
)
from supersub_agent.pose import extract_keypoints  # noqa: E402

HERE = Path(__file__).resolve().parent
CLIPS = Path("/mnt/d/sports-pose/soccer/motion_id")

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
SPEED_SHOT = 42.0      # 어깨너비/초
SPEED_PASS = 25.0
RISE_SHOT = 6.0
FOLLOW_SHOT = 30.0     # 도 — 두 루브릭의 2등급 경계에서 그대로 가져왔다
FOLLOW_PASS = 25.0
KNEE_SHOT = 600.0      # 도/초
KNEE_PASS = 300.0
BALL_WINDOW = 0.25     # 초
MIN_BALL_FRAMES = 3
# 계기 검사 — 이 값을 넘으면 분류 실패가 아니라 **대상 선택 실패**다(미결 45번).
SUBJECT_FAIL_DIST = 1.2

# 🔴 `extract_keypoints` 의 기본 상한은 **10초**다 (제품 입력이 짧은 클립
#    하나라서). 여기 표본은 강의 영상이라 앞 10초가 말하는 장면일 수 있고,
#    그러면 **동작을 못 본 채** 「분류 실패」로 적히게 된다. 그래서 늘린다.
#    `segment_phases` 는 구간 전체에서 신전 각속도 최대점 **하나**를 고르므로,
#    반복 동작이 여러 번 나와도 그중 한 번을 잡는다 — 이 회차가 묻는 것은
#    「몇 번인가」가 아니라 「어느 동작인가」라 그것으로 충분하다.
MAX_SECONDS = 40.0


def ball_signals(kps: np.ndarray, ball: np.ndarray, impact: int,
                 fps: float) -> dict:
    """임팩트 직후 공의 이탈 속도·상승. 못 재면 값이 None.

    🔴 production 정규화를 그대로 쓴다 — 골반 중심 원점이라 값이 **선수 기준
    상대량**이 되고, 카메라 팬이 상당 부분 상쇄된다.
    """
    nb = normalize_track(ball, kps)
    span = max(1, int(round(BALL_WINDOW * fps)))
    lo, hi = impact, min(len(nb) - 1, impact + span)

    seen = [t for t in range(lo, hi + 1) if nb[t, 2] > 0]
    if len(seen) < MIN_BALL_FRAMES:
        return {"ball_speed": None, "ball_rise": None,
                "ball_frames": len(seen), "ball_coverage": float((nb[:, 2] > 0).mean())}

    t0, t1 = seen[0], seen[-1]
    dt = (t1 - t0) / fps
    if dt <= 0:
        return {"ball_speed": None, "ball_rise": None,
                "ball_frames": len(seen), "ball_coverage": float((nb[:, 2] > 0).mean())}

    d = nb[t1, :2] - nb[t0, :2]
    speed = float(np.hypot(*d) / dt)
    # 이미지 y는 아래로 증가한다 — 위로 뜨면 dy가 음수다.
    rise = float(-d[1] / dt)
    return {"ball_speed": round(speed, 2), "ball_rise": round(rise, 2),
            "ball_frames": len(seen),
            "ball_coverage": round(float((nb[:, 2] > 0).mean()), 3)}


def nearest_foot_to_ball(kps: np.ndarray, ball: np.ndarray, impact: int) -> float | None:
    """임팩트 시점 공↔가까운 발목 거리 (어깨너비). 계기 검사용."""
    nk, nb = normalize(kps), normalize_track(ball, kps)
    if nb[impact, 2] <= 0:
        cand = [t for t in range(max(0, impact - 2), min(len(nb), impact + 3))
                if nb[t, 2] > 0]
        if not cand:
            return None
        impact = min(cand, key=lambda t: abs(t - impact))
    return float(min(
        np.hypot(*(nk[impact, a, :2] - nb[impact, :2])) for a in (L_ANKLE, R_ANKLE)
    ))


def knee_angular_velocity(kps: np.ndarray, swing_knee: int, impact: int,
                          fps: float) -> float | None:
    """임팩트 시 스윙 무릎의 신전 각속도 (도/초).

    🔴 각도 식을 여기 옮겨 적지 않는다 — `chain_series` 가 production 의
    무릎각 시계열이고, `segment_phases` 가 임팩트를 찾을 때 미분하는 것도
    **바로 이 계열**이다. 다시 쓰면 둘이 조용히 갈라진다.
    """
    side = "left" if swing_knee == L_KNEE else "right"
    series = chain_series(kps, LIMB_CHAINS["leg"][side])
    if not np.isfinite(series).any():
        return None
    g = np.gradient(series) * fps
    if not np.isfinite(g[impact]):
        return None
    return round(float(abs(g[impact])), 1)


def vote(sig: dict) -> tuple[str, dict, float]:
    """사전 등록한 규칙으로 표를 센다. 동률·표 부족이면 unknown."""
    votes: dict[str, str] = {}
    shot = pass_ = 0.0

    s = sig.get("ball_speed")
    if s is not None:
        if s >= SPEED_SHOT:
            votes["S1"] = "shot"; shot += 1.0
        elif s <= SPEED_PASS:
            votes["S1"] = "pass"; pass_ += 1.0
        else:
            votes["S1"] = "기권"
    else:
        votes["S1"] = "측정불가"

    r = sig.get("ball_rise")
    if r is not None:
        if r >= RISE_SHOT:
            votes["S2"] = "shot"; shot += 1.0
        else:
            votes["S2"] = "기권"     # 안 뜬다고 패스는 아니다 (사전 등록)
    else:
        votes["S2"] = "측정불가"

    f = sig.get("follow_through")
    if f is not None:
        if f >= FOLLOW_SHOT:
            votes["S3"] = "shot"; shot += 1.0
        elif f <= FOLLOW_PASS:
            votes["S3"] = "pass"; pass_ += 1.0
        else:
            votes["S3"] = "기권"
    else:
        votes["S3"] = "측정불가"

    k = sig.get("knee_ang_vel")
    if k is not None:
        if k >= KNEE_SHOT:
            votes["S4"] = "shot"; shot += 0.5
        elif k <= KNEE_PASS:
            votes["S4"] = "pass"; pass_ += 0.5
        else:
            votes["S4"] = "기권"
    else:
        votes["S4"] = "측정불가"

    total = shot + pass_
    if total < 1.0 or shot == pass_:
        return "unknown", votes, total
    return ("shot" if shot > pass_ else "pass"), votes, total


def measure(path: Path, label: str) -> dict:
    row: dict = {"clip": path.name, "label": label}
    try:
        pose = extract_keypoints(path, observe=False, max_seconds=MAX_SECONDS)
    except Exception as exc:                       # noqa: BLE001
        row["error"] = f"pose: {type(exc).__name__}: {exc}"
        return row

    kps, fps = pose.keypoints, pose.sampled_fps
    row["frames"] = int(len(kps))
    row["fps"] = round(float(fps), 2)
    # 상한에 걸려 뒷부분을 안 봤는가 — 결과를 읽을 때 필요하다.
    row["truncated"] = bool(pose.truncated)

    try:
        swing_knee, _ = identify_legs(kps, "auto")
        phases = segment_phases(kps, swing_knee, "leg", "extension_peak")
    except InsufficientQuality as exc:
        row["error"] = f"phase: {exc}"
        return row
    impact = phases.impact
    row["impact"] = int(impact)

    # 팔로스루는 production 지표를 그대로 쓴다 — 식을 여기 옮겨 적지 않는다.
    try:
        feats = extract_features(kps, pose.objects, "leg", "extension_peak", "auto")
    except InsufficientQuality as exc:
        row["error"] = f"features: {exc}"
        return row
    row["follow_through"] = feats.get("swing_hip_flexion_after_impact_deg")
    row["knee_ang_vel"] = knee_angular_velocity(kps, swing_knee, impact, fps)

    ball = (pose.objects or {}).get("sports_ball")
    if ball is None:
        row.update({"ball_speed": None, "ball_rise": None,
                    "ball_frames": 0, "ball_coverage": 0.0, "foot_ball": None})
    else:
        row.update(ball_signals(kps, ball, impact, fps))
        row["foot_ball"] = nearest_foot_to_ball(kps, ball, impact)

    pred, votes, weight = vote(row)
    row["pred"] = pred
    row["votes"] = votes
    row["vote_weight"] = weight
    return row


def main() -> int:
    manifest = list(csv.DictReader(
        (HERE / "clips_manifest.csv").open(encoding="utf-8")))
    print(f"클립 {len(manifest)}편\n", flush=True)

    rows = []
    t0 = time.time()
    for i, m in enumerate(manifest, 1):
        path = CLIPS / m["path"]
        if not path.exists():
            print(f"[{i}/{len(manifest)}] ⊘ 없음 {m['path']}", flush=True)
            continue
        row = measure(path, m["label"])
        row["title"] = m["title"]
        rows.append(row)
        mark = row.get("error") or f"{row.get('pred')} (표 {row.get('vote_weight')})"
        print(f"[{i}/{len(manifest)}] {m['label']:12s} {path.name[:16]:18s} {mark}",
              flush=True)

    out = HERE / "motion_raw.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n원자료 {out} · {time.time() - t0:.0f}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
