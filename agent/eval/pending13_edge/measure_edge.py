#!/usr/bin/env python3
"""미결 13번 — `np.gradient` 끝단 단측차분이 오염에 얼마나 더 취약한지 잰다.

**처방을 고르지 않는다.** 항목이 "아직 아무것도 정하지 않았다"고 적어 둔 상태라,
여기서는 무엇이 얼마나 일어나는지만 센다. 어느 처방이 옳은지는 미결 5번의
정답이 필요하다.

재는 것 넷:

  (1) 임팩트로 뽑힌 프레임이 **유효 구간의 끝단**인 비율
  (2) 이긴 프레임의 각속도가 **usable이 아닌 이웃**에서 계산됐는지
  (3) 오염된 이웃을 뺐을 때 argmax가 옮겨가는지 (옮겨간다 = 오염이 이겼다)
  (4) 끝단 단측차분과 안쪽 중심차분의 **잡음 증폭 비**

  usage:
    uv run python eval/pending13_edge/measure_edge.py [--target 30|15] [--cache DIR] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phaseA"))
from supersub_agent import features as F  # noqa: E402
from paths import cache_dir  # noqa: E402

CONFIGS = {
    "arm_ext_auto": ("arm", "auto"),
    "leg_ext_auto": ("leg", "auto"),
}


def neighbours(i: int, n: int) -> list[int]:
    """np.gradient 가 i 의 미분에 실제로 쓰는 프레임들.

    안쪽은 중심차분이라 i-1·i+1 을 쓰고 **i 자신은 안 쓴다.**
    끝단은 단측차분이라 이웃이 하나뿐이다 — 그 하나가 오염되면 희석이 없다.
    """
    if n < 2:
        return []
    if i == 0:
        return [0, 1]
    if i == n - 1:
        return [n - 2, n - 1]
    return [i - 1, i + 1]


def analyse_clip(kps: np.ndarray, limb: str, side: str) -> dict | None:
    try:
        swing, _ = F.identify_limb(kps, limb, side)
    except Exception:
        return None

    series = F.chain_series(kps, swing)
    usable = F.valid_frames(kps, limb, swing) & np.isfinite(series)
    if not usable.any():
        return None

    n = len(series)
    vel = np.gradient(series)

    try:
        impact = F._peak_frame(vel, usable)
    except F.InsufficientQuality:
        return None

    first = int(np.argmax(usable))
    last = int(n - 1 - np.argmax(usable[::-1]))

    # 오염원은 **usable 이 아닌데 각도는 유한한** 프레임이다. 완전 미검출은
    # joint_angle 이 NaN 을 내고 그 NaN 이 gradient 로 번져 후보에서 빠지므로
    # 이미 걸러진다. 문제는 신뢰도만 낮고 좌표는 그럴듯한 프레임이다 —
    # 유한한 쓰레기 각도가 그대로 속도가 된다.
    finite_garbage = (~usable) & np.isfinite(series)

    used = neighbours(impact, n)
    contaminated = [j for j in used if finite_garbage[j]]

    # 오염원을 빼고 다시 뽑으면 argmax 가 옮겨가는가.
    # (처방이 아니라 **오염이 결과를 바꿨는지** 보는 대조군이다.)
    clean = series.copy()
    clean[finite_garbage] = np.nan
    vel_clean = np.gradient(clean)
    try:
        impact_clean = F._peak_frame(vel_clean, usable)
    except F.InsufficientQuality:
        impact_clean = None

    return {
        "n": n,
        "impact": impact,
        "first": first,
        "last": last,
        "at_edge": impact in (first, last),
        "at_array_edge": impact in (0, n - 1),
        "vel": float(vel[impact]),
        "neighbours_used": used,
        "contaminated_neighbours": contaminated,
        "n_finite_garbage": int(finite_garbage.sum()),
        "n_usable": int(usable.sum()),
        "impact_clean": impact_clean,
        "moved": impact_clean is not None and impact_clean != impact,
        # 경계 규칙(segment_phases)이 반려하는가
        "rejected_by_edge_rule": (impact - first < 2) or (last - impact < 2),
        "rejected_clean": (
            None if impact_clean is None
            else (impact_clean - first < 2) or (last - impact_clean < 2)
        ),
    }


def noise_amplification(series: np.ndarray, usable: np.ndarray) -> float | None:
    """끝단 단측차분이 안쪽 중심차분보다 잡음을 몇 배로 키우는가.

    같은 신호에 대해 두 공식을 모든 안쪽 프레임에 적용해 표준편차를 비교한다.
    이론값은 백색잡음 가정에서 2.0 이다 — 중심차분이 2로 나누기 때문이다.
    실제 신호는 상관이 있어 그보다 작게 나온다.
    """
    s = np.where(usable, series, np.nan)
    central, onesided = [], []
    for i in range(1, len(s) - 1):
        if np.isfinite(s[i - 1]) and np.isfinite(s[i + 1]):
            central.append((s[i + 1] - s[i - 1]) / 2.0)
        if np.isfinite(s[i]) and np.isfinite(s[i + 1]):
            onesided.append(s[i + 1] - s[i])
    if len(central) < 5 or len(onesided) < 5:
        return None
    sc, so = float(np.std(central)), float(np.std(onesided))
    return so / sc if sc > 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=30, choices=(15, 30),
                    help="동작점 target_fps (기본 30 — 현재 동작점)")
    ap.add_argument("--cache", type=Path, help="캐시 폴더를 직접 지정 (--target 무시)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    try:
        cache = args.cache if args.cache else cache_dir(args.target)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    if not cache.is_dir():
        print(f"캐시 폴더가 없다: {cache}", file=sys.stderr)
        return 2

    paths = sorted(p for p in cache.glob("*.npz") if ".ERROR" not in p.name)
    if not paths:
        print(f"npz 가 없다: {cache}", file=sys.stderr)
        return 2

    out: dict[str, dict] = {}
    amps: list[float] = []
    frames_seen: list[int] = []

    for p in paths:
        d = np.load(p, allow_pickle=True)
        kps = d["keypoints"]
        frames_seen.append(kps.shape[0])
        per: dict[str, dict] = {}
        for tag, (limb, side) in CONFIGS.items():
            r = analyse_clip(kps, limb, side)
            if r is not None:
                per[tag] = r
                if tag == "arm_ext_auto":
                    try:
                        swing, _ = F.identify_limb(kps, limb, side)
                        series = F.chain_series(kps, swing)
                        usable = F.valid_frames(kps, limb, swing) & np.isfinite(series)
                        a = noise_amplification(series, usable)
                        if a is not None:
                            amps.append(a)
                    except Exception:
                        pass
        out[p.stem] = per

    print(f"캐시: {cache}")
    print(f"클립 {len(paths)}개 · 프레임 수 {min(frames_seen)}~{max(frames_seen)}\n")

    for tag in CONFIGS:
        rs = [r[tag] for r in out.values() if tag in r]
        if not rs:
            continue
        n = len(rs)
        edge = [r for r in rs if r["at_edge"]]
        cont = [r for r in rs if r["contaminated_neighbours"]]
        edge_cont = [r for r in edge if r["contaminated_neighbours"]]
        moved = [r for r in rs if r["moved"]]
        rej = [r for r in rs if r["rejected_by_edge_rule"]]

        print(f"[{tag}] 산출된 클립 {n}개")
        print(f"  임팩트가 유효 구간 끝단          {len(edge):3d}  ({len(edge)/n:.0%})")
        print(f"  이긴 프레임의 이웃이 오염됨      {len(cont):3d}  ({len(cont)/n:.0%})")
        print(f"    그중 끝단이기도 한 것          {len(edge_cont):3d}")
        print(f"  오염을 빼면 argmax 가 옮겨감     {len(moved):3d}  ({len(moved)/n:.0%})")
        print(f"  경계 규칙이 반려                 {len(rej):3d}")
        if moved:
            print("  옮겨간 클립:")
            for cid, r in out.items():
                if tag in r and r[tag]["moved"]:
                    m = r[tag]
                    print(f"    {cid:16s} f{m['impact']:>3d} -> f{m['impact_clean']:>3d}"
                          f"  (구간 {m['first']}~{m['last']}, 속도 {m['vel']:+.1f},"
                          f" 오염이웃 {m['contaminated_neighbours']})")
        print()

    if amps:
        print(f"끝단 단측차분 / 안쪽 중심차분 잡음 비: "
              f"중앙값 {np.median(amps):.3f}  (평균 {np.mean(amps):.3f}, n={len(amps)})")
        print("  이론값은 백색잡음 가정에서 2.0 이다. 실제 신호는 상관이 있어 더 작다.")

    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"\n-> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
