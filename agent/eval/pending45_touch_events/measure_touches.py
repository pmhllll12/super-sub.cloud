"""공-발 거리로 터치 이벤트를 여럿 찾을 수 있는가 — 1회차 (미결 `ho` 45번 ㉲-a).

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `1940afb`)을 먼저 읽는다.** 상수와
합격선은 이 파일을 쓰기 전에 굳혔고 결과를 보고 고치지 않는다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. production 은 **import 만**
하고, 이 회차 전용 규칙(극소점 찾기)만 여기 둔다.

    cd agent && uv run python eval/pending45_touch_events/measure_touches.py
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

from supersub_agent.features import (  # noqa: E402
    L_ANKLE,
    R_ANKLE,
    InsufficientQuality,
    normalize,
    normalize_track,
    segment_phases,
)
from supersub_agent.features import LIMB_CHAINS  # noqa: E402
from supersub_agent.pose import extract_keypoints  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
CONTACT_MAX = 0.8      # 어깨너비 단위
MIN_GAP = 8            # 프레임
MIN_BALL_COVERAGE = 0.30
MATCH_TOLERANCE = 5    # 기존 impact_frame 과 몇 프레임까지 같다고 볼 것인가


def ball_foot_distance(kps: np.ndarray, ball: np.ndarray) -> np.ndarray:
    """프레임별 공↔가까운 발목 거리 (어깨너비 단위). 잴 수 없으면 NaN.

    🔴 공과 키포인트를 **같은 정규화**로 옮긴다 — `normalize_track` 이
    production 의 규칙이다. 원 픽셀로 재면 해상도마다 값이 달라진다.
    """
    norm_kps = normalize(kps)
    norm_ball = normalize_track(ball, kps)
    out = np.full(len(kps), np.nan)
    for t in range(len(kps)):
        if norm_ball[t, 2] <= 0:          # 그 프레임에 공이 안 잡혔다
            continue
        best = np.inf
        for ankle in (L_ANKLE, R_ANKLE):
            if norm_kps[t, ankle, 2] <= 0:
                continue
            best = min(best, float(np.hypot(*(norm_ball[t, :2] - norm_kps[t, ankle, :2]))))
        if np.isfinite(best):
            out[t] = best
    return out


def find_touches(d: np.ndarray) -> list[int]:
    """`d` 의 국소 극소점 중 터치로 볼 것들 (프레임 인덱스).

    규칙은 사전 등록 그대로다 — `d ≤ CONTACT_MAX` 이고 서로 `MIN_GAP` 이상
    떨어진 것. 겹치면 **더 가까운 쪽**을 남긴다.

    🔴 NaN(공 미검출)은 극소점 후보가 아니다. 끊긴 구간을 이어 붙이면
    없는 접근을 지어낸다.
    """
    cand: list[int] = []
    for t in range(len(d)):
        if not np.isfinite(d[t]) or d[t] > CONTACT_MAX:
            continue
        prev = d[t - 1] if t > 0 and np.isfinite(d[t - 1]) else np.inf
        nxt = d[t + 1] if t + 1 < len(d) and np.isfinite(d[t + 1]) else np.inf
        if d[t] <= prev and d[t] <= nxt:
            cand.append(t)
    # 가까운 순으로 집고, 이미 뽑은 것과 MIN_GAP 안이면 버린다.
    kept: list[int] = []
    for t in sorted(cand, key=lambda i: d[i]):
        if all(abs(t - k) >= MIN_GAP for k in kept):
            kept.append(t)
    return sorted(kept)


def main() -> None:
    clips = sorted(paths.soccer_clips_root().rglob("*.avi"))
    print(f"축구 세트피스 {len(clips)}편 · CONTACT_MAX={CONTACT_MAX} "
          f"MIN_GAP={MIN_GAP}\n")

    rows = []
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            pose = extract_keypoints(clip, observe=False)
        except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 회차는 돈다
            print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} ⚠️ {type(exc).__name__}")
            rows.append({"clip": clip.name, "error": repr(exc)})
            continue

        ball = pose.objects.get("sports_ball")
        n = len(pose.keypoints)
        if ball is None:
            rows.append({"clip": clip.name, "frames": n, "ball_coverage": 0.0,
                         "skipped": "공 궤적 없음"})
            print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} 공 없음")
            continue

        d = ball_foot_distance(pose.keypoints, ball)
        coverage = float(np.isfinite(d).mean())
        touches = find_touches(d)

        # 기존 파이프라인의 단일 임팩트 — 비교용이다.
        try:
            chain = LIMB_CHAINS["leg"]["right"]
            impact = segment_phases(normalize(pose.keypoints), chain, "leg",
                                    "extension_peak").impact
        except (InsufficientQuality, ValueError):
            impact = None

        nearest = min(touches, key=lambda t: d[t]) if touches else None
        # 🔴 **계기 검사용 관측이다 — 판정에 안 쓴다.** 터치가 0이 나왔을 때
        #    「문턱에 아깝게 걸렸나」와 「공이 아예 딴 데 있나」를 갈라야
        #    다음 회차의 방향이 정해진다. 사전 등록의 합격선은 그대로다.
        finite = d[np.isfinite(d)]
        rows.append({
            "clip": clip.name, "frames": n,
            "ball_coverage": round(coverage, 3),
            "distance_min": round(float(finite.min()), 3) if finite.size else None,
            "distance_p10": round(float(np.percentile(finite, 10)), 3) if finite.size else None,
            "distance_median": round(float(np.median(finite)), 3) if finite.size else None,
            "touches": touches,
            "n_touches": len(touches),
            "nearest_touch": nearest,
            "nearest_distance": round(float(d[nearest]), 3) if nearest is not None else None,
            "legacy_impact": impact,
            "gap_to_legacy": (abs(nearest - impact)
                              if nearest is not None and impact is not None else None),
            "seconds": round(time.time() - t0, 1),
        })
        print(f"  [{i}/{len(clips)}] {clip.name[:34]:34s} "
              f"터치 {len(touches):2d} · 공커버 {coverage:.0%} · "
              f"최근접 {rows[-1]['distance_min']} · "
              f"임팩트 {impact} vs 터치 {nearest}  ({rows[-1]['seconds']}초)")

    (HERE / "touches_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [r for r in rows if r.get("ball_coverage", 0) >= MIN_BALL_COVERAGE
          and "error" not in r and "skipped" not in r]
    dropped = [r for r in rows if r not in ok]

    print("\n" + "=" * 66)
    print(f"분모 {len(ok)}/{len(clips)} 편 "
          f"(공 커버리지 <{MIN_BALL_COVERAGE:.0%} 등으로 뺀 것 {len(dropped)}편)")
    if not ok:
        print("🔴 분모가 비었다 — 판정할 수 없다")
        return

    counts = [r["n_touches"] for r in ok]
    med = statistics.median(counts)
    matched = [r for r in ok if r["gap_to_legacy"] is not None
               and r["gap_to_legacy"] <= MATCH_TOLERANCE]
    comparable = [r for r in ok if r["gap_to_legacy"] is not None]
    rate = len(matched) / len(comparable) if comparable else 0.0

    print(f"터치 수: 중앙값 {med} · 분포 {sorted(counts)}")
    print(f"기존 임팩트와 ±{MATCH_TOLERANCE}프레임 일치: "
          f"{len(matched)}/{len(comparable)} ({rate:.0%})")

    print("\n── 사전 등록 판정")
    print(f"  A 터치 수 중앙값 1~3        : {med} {'✅' if 1 <= med <= 3 else '🔴'}")
    print(f"  B 기존 임팩트와 일치 ≥50%   : {rate:.0%} {'✅' if rate >= 0.5 else '🔴'}")
    print("  C production 무수정         : ✅ (이 스크립트는 import 만 한다)")
    print(f"  D 뺀 클립                   : {len(dropped)}편 "
          f"{[r['clip'] for r in dropped] or ''}")
    print("\n🔴 B 의 일치는 **「맞다」가 아니다** — 둘 다 검증 안 된 계기다.")
    print("🔴 이 표본은 **단일 동작**이라 「여럿 찾는다」는 증명되지 않는다.")

    # ── 사후 관찰 (판정에 안 쓴다) ─────────────────────────────────────
    mins = [r["distance_min"] for r in ok if r.get("distance_min") is not None]
    if mins:
        near_miss = [m for m in mins if CONTACT_MAX < m <= CONTACT_MAX * 1.5]
        print(f"\n── 사후 관찰 (판정에 안 쓴다)")
        print(f"  클립별 최근접 거리: 중앙값 {statistics.median(mins):.2f} "
              f"어깨너비 · 범위 {min(mins):.2f}~{max(mins):.2f}")
        print(f"  문턱({CONTACT_MAX}) 바로 위(~{CONTACT_MAX * 1.5}) 인 클립: "
              f"{len(near_miss)}/{len(mins)}")
        print("  🔴 문턱 근처가 적고 전반적으로 멀면 **문턱 문제가 아니라**")
        print("     추적 대상이 공 가진 사람이 아닐 가능성이 크다 (미결 18번).")


if __name__ == "__main__":
    main()
