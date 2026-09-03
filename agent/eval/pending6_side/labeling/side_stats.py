#!/usr/bin/env python3
"""미결 6번 — 39클립의 자동 스윙 측 판별 결과·마진·fps 갈림을 낸다.

**판독 패킷에는 이 값이 들어가지 않는다.** 라벨을 매기는 사람이 자동 판별을
먼저 보면 앵커링이 생긴다(B-4 선례가 같은 이유로 후보 상자를 전부 같은
색으로 그렸다). 여기서 낸 표는 **라벨이 채워진 뒤** 대조용으로만 쓴다.

판별 로직은 건드리지 않는다 — `features.identify_limb`이 쓰는 travel 정의를
그대로 다시 계산해 마진만 덧붙인다.

    uv run python eval/pending6_side/labeling/side_stats.py [--out CSV]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent.parent
sys.path.insert(0, str(AGENT / "src"))
sys.path.insert(0, str(AGENT / "eval" / "phaseA"))

from supersub_agent.features import LIMB_CHAINS  # noqa: E402
from paths import cache_dir  # noqa: E402


def travel(kps: np.ndarray, chain) -> float:
    """`identify_limb`의 travel 그대로 — 말단 관절 이동 거리의 합."""
    distal = chain[2]
    xy = kps[:, :, :2]
    return float(np.linalg.norm(np.diff(xy[:, distal], axis=0), axis=1).sum())


def decide(kps: np.ndarray, limb: str) -> tuple[str, float, float, float]:
    """(자동이 고르는 쪽, left travel, right travel, 마진).

    마진 = |L − R| / max(L, R). `identify_limb`은 동률에서 left를 고른다.
    """
    left = travel(kps, LIMB_CHAINS[limb]["left"])
    right = travel(kps, LIMB_CHAINS[limb]["right"])
    side = "left" if left >= right else "right"
    hi = max(left, right)
    margin = abs(left - right) / hi if hi > 0 else 0.0
    return side, left, right, margin


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "reference_AFTER_LABELING.csv")
    args = ap.parse_args()

    c30, c15 = cache_dir(30), cache_dir(15)
    clips = sorted(p.stem for p in c30.glob("*.npz") if ".ERROR" not in p.name)

    rows = []
    exact_by_clip: list[dict[str, float]] = []
    for cid in clips:
        k30 = np.load(c30 / f"{cid}.npz", allow_pickle=True)["keypoints"]
        p15 = c15 / f"{cid}.npz"
        k15 = np.load(p15, allow_pickle=True)["keypoints"] if p15.exists() else None

        row = {"clip_id": cid}
        exact: dict[str, float] = {}      # 집계는 반올림 전 값으로 한다 —
        exact_by_clip.append(exact)       # 0.049996 을 반올림하면 경계가 밀린다
        for limb in ("arm", "leg"):
            s30, l30, r30, m30 = decide(k30, limb)
            exact[limb] = m30
            row[f"auto_{limb}_30"] = s30
            row[f"margin_{limb}_30"] = round(m30, 4)
            row[f"travel_{limb}_left_30"] = round(l30, 2)
            row[f"travel_{limb}_right_30"] = round(r30, 2)
            if k15 is not None:
                s15, _, _, m15 = decide(k15, limb)
                row[f"auto_{limb}_15"] = s15
                row[f"margin_{limb}_15"] = round(m15, 4)
                row[f"flips_{limb}_15v30"] = int(s15 != s30)
            else:
                row[f"auto_{limb}_15"] = ""
                row[f"margin_{limb}_15"] = ""
                row[f"flips_{limb}_15v30"] = ""
        # 팔 측과 다리 측이 같은가 — 39클립에서 44%만 일치한다는 기록의 확인
        row["arm_leg_agree_30"] = int(row["auto_arm_30"] == row["auto_leg_30"])
        rows.append(row)

    cols = list(rows[0])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    print(f"클립 {n}개 → {args.out}\n")
    for limb in ("arm", "leg"):
        flips = sum(r[f"flips_{limb}_15v30"] == 1 for r in rows)
        thin = sum(e[limb] < 0.05 for e in exact_by_clip)
        thin10 = sum(e[limb] < 0.10 for e in exact_by_clip)
        med = np.median([e[limb] for e in exact_by_clip])
        print(f"[{limb}] 15fps↔30fps 갈림 {flips}/{n} · "
              f"마진 5% 미만 {thin}/{n} · 10% 미만 {thin10}/{n} · 중앙값 {med:.3f}")
    agree = sum(r["arm_leg_agree_30"] for r in rows)
    print(f"\n팔 측과 다리 측이 같은 클립: {agree}/{n} ({agree/n:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
