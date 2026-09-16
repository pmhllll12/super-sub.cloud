"""1회차의 `ball_speed` 가 무엇을 재고 있었나 — 캐시로 GPU 없이 (미결 `ho` 52번 2회차).

🔴 **판정 회차가 아니다.** 사전 등록이 없고 합격선도 없다. 여기 숫자는
**1회차가 왜 그런 값을 냈는지**를 알아보는 것이고, 처방을 고르는 근거로 쓰려면
사전 등록을 세우고 다시 재야 한다.

1회차 `RESULTS.md` 가 남긴 후보 셋을 가른다:

  (가) 40초 클립에서 `segment_phases` 의 **전역 최대점이 실제 킥이 아니다**
  (나) 검출된 `sports_ball` 이 **찬 공이 아니다**
  (다) 골반 중심 정규화가 카메라 팬과 함께 **공의 이동까지 상쇄한다**

가르는 방법: 클립 **전체**에서 공의 프레임별 속도를 구해 **어디가 가장 빠른지**를
보고, 그 지점이 `impact_frame` 과 얼마나 떨어져 있는지 센다.

  - 최대 속도가 **임팩트 근처**인데 값이 작다 → (다) 쪽. 정규화를 의심한다
  - 최대 속도가 **딴 데**서 크다 → (가). 임팩트를 잘못 잡은 것이다
  - 클립 어디에도 빠른 구간이 **없다** → (나). 공이 딴 것이다

    cd agent && uv run python eval/pending52_motion_id/diagnose_impact.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    identify_legs,
    normalize_track,
    segment_phases,
)

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = paths.motion_id_cache()

NEAR = 5          # 임팩트와 몇 프레임까지 「근처」로 볼 것인가
SMOOTH = 3        # 속도 계열을 몇 프레임으로 다듬을 것인가


def ball_speed_series(kps: np.ndarray, ball: np.ndarray,
                      fps: float) -> np.ndarray:
    """프레임별 공 속도 (어깨너비/초). 못 재는 프레임은 NaN.

    🔴 **정규화된 좌표와 원 좌표를 둘 다 낸다** — 후보 (다)를 가르려면
    정규화가 무엇을 없애는지 봐야 한다. 여기서는 정규화 쪽이다.
    """
    nb = normalize_track(ball, kps)
    seen = nb[:, 2] > 0
    out = np.full(len(nb), np.nan)
    idx = np.flatnonzero(seen)
    for a, b in zip(idx[:-1], idx[1:]):
        gap = b - a
        if gap > SMOOTH:           # 너무 벌어진 구간은 속도로 치지 않는다
            continue
        d = np.hypot(*(nb[b, :2] - nb[a, :2]))
        out[a] = d / (gap / fps)
    return out


def raw_speed_series(ball: np.ndarray, fps: float,
                     scale: float) -> np.ndarray:
    """정규화 **전** 좌표로 잰 속도 (같은 어깨너비 단위로 나누기만 한다).

    골반 중심을 빼지 않으므로 선수 이동·카메라 팬이 남는다. 정규화본과 크게
    다르면 (다)가 산다.
    """
    seen = ball[:, 2] > 0
    out = np.full(len(ball), np.nan)
    idx = np.flatnonzero(seen)
    for a, b in zip(idx[:-1], idx[1:]):
        gap = b - a
        if gap > SMOOTH:
            continue
        d = np.hypot(*(ball[b, :2] - ball[a, :2])) / scale
        out[a] = d / (gap / fps)
    return out


def main() -> int:
    manifest = list(csv.DictReader(
        (HERE / "clips_manifest.csv").open(encoding="utf-8")))

    print(f"{'라벨':11s} {'클립':13s} {'임팩트':>6s} {'프레임':>6s} "
          f"{'임팩트속도':>9s} {'최대속도':>8s} {'최대위치':>7s} {'거리':>5s} "
          f"{'원좌표최대':>9s}")
    print("-" * 92)

    rows = []
    for m in manifest:
        npz = CACHE / m["label"] / f"{m['id']}.npz"
        if not npz.exists():
            continue
        d = np.load(npz, allow_pickle=False)
        if str(d["error"]):
            continue
        kps = d["keypoints"].astype(np.float64)
        ball = d["ball"].astype(np.float64)
        fps = float(d["sampled_fps"])
        if len(ball) == 0:
            print(f"{m['label'][:10]:11s} {m['id'][:12]:13s} 공 궤적 없음")
            continue

        try:
            swing_knee, _ = identify_legs(kps, "auto")
            impact = segment_phases(kps, swing_knee, "leg", "extension_peak").impact
        except InsufficientQuality as exc:
            print(f"{m['label'][:10]:11s} {m['id'][:12]:13s} 임팩트 못 잡음: "
                  f"{str(exc)[:40]}")
            continue

        try:
            from supersub_agent.features import normalization_params
            _, scale = normalization_params(kps)
        except InsufficientQuality:
            continue

        v = ball_speed_series(kps, ball, fps)
        vr = raw_speed_series(ball, fps, scale)
        if not np.isfinite(v).any():
            print(f"{m['label'][:10]:11s} {m['id'][:12]:13s} 속도를 못 잼")
            continue

        peak = int(np.nanargmax(v))
        at_impact = v[impact] if np.isfinite(v[impact]) else np.nan
        dist = abs(peak - impact)
        raw_peak = float(np.nanmax(vr)) if np.isfinite(vr).any() else float("nan")

        print(f"{m['label'][:10]:11s} {m['id'][:12]:13s} {impact:6d} "
              f"{len(kps):6d} {at_impact:9.1f} {np.nanmax(v):8.1f} "
              f"{peak:7d} {dist:5d} {raw_peak:9.1f}")
        rows.append({"label": m["label"], "id": m["id"], "impact": impact,
                     "at_impact": at_impact, "peak_v": float(np.nanmax(v)),
                     "peak_at": peak, "dist": dist, "raw_peak": raw_peak})

    if not rows:
        print("\n캐시가 비어 있다 — 먼저 cache_poses.py 를 돌릴 것.")
        return 1

    near = [r for r in rows if r["dist"] <= NEAR]
    print(f"\n## 최대 속도가 임팩트 근처(±{NEAR}프레임)인 클립: "
          f"**{len(near)}/{len(rows)}**")
    print(f"- 임팩트↔최대 거리 중앙값 **{np.median([r['dist'] for r in rows]):.0f}프레임**")
    print(f"- 임팩트 시점 속도 중앙값 {np.nanmedian([r['at_impact'] for r in rows]):.1f} "
          f"· 클립 최대 속도 중앙값 **{np.median([r['peak_v'] for r in rows]):.1f}** 어깨너비/초")
    print(f"- 정규화 **전** 좌표의 최대 속도 중앙값 {np.median([r['raw_peak'] for r in rows]):.1f}")

    print("\n### 읽는 법 (사전에 적어 둔다)")
    print("- 최대가 임팩트 근처인데 값이 작다 → **(다) 정규화**를 의심한다")
    print("- 최대가 딴 데서 크다 → **(가) 임팩트를 잘못 잡았다**")
    print("- 어디에도 빠른 구간이 없다 → **(나) 검출된 공이 찬 공이 아니다**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
