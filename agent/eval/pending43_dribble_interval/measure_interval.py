"""드리블 터치 간격을 잰다 — 미결 `ho` 43번 ㉳ (다).

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `423b6d0`)을 먼저 읽는다.** 상수·
합격선·판별 규칙·예측은 이 파일을 쓰기 **전에** 굳었고 결과를 보고 고치지 않는다.

🔴 **11회차 계기를 고치지 않고 `import` 한다** (`measure_proximity`). 복제하면
두 회차의 계기가 조용히 갈라진다(미결 10번의 형태). 이 파일이 얹는 것은
**에피소드와 간격**뿐이다.

🔴 **`src/` 를 한 줄도 안 고친다** — 조사 회차다. ViTPose 는 안 돌린다(검출만).

    cd agent && uv run python eval/pending43_dribble_interval/measure_interval.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_ball_proximity"))

from measure_proximity import (  # noqa: E402
    MIN_BALL_COVERAGE,
    NEAR,
    NEAR_SWEEP,
    analyse,
    detect_clip,
)
from supersub_agent.pose import _load_detector  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent

#: 사전 등록 기준 A — 이 아래면 판별불가.
MIN_INTERVALS = 30
#: 사전 등록 기준 E — 야구 대조군이 이 이상이면 계기가 딴 것을 센다.
CONTROL_MAX = 10
#: 비교 대상 — 1·2회차가 굵게 둔 가정값.
ASSUMED = (10, 15)
#: 간격을 30fps 기준으로 환산한다 (SoccerNet 원본은 25fps).
NORMALISE_FPS = 30.0


def episodes(rows: list[dict], near: float) -> list[tuple[int, int]]:
    """근접 프레임의 연속 덩어리 — (시작 t, 끝 t).

    🔴 `rows` 는 **공이 잡힌 프레임만** 담는다(`analyse` 가 그렇게 만든다).
    그래서 `t` 가 건너뛰는 자리가 곧 **추적이 끊긴 자리**이고, 아래
    `intervals()` 가 그 자리를 넘는 간격을 버린다.
    """
    near_ts = [r["t"] for r in rows if r["d_min"] <= near]
    if not near_ts:
        return []
    out, start, prev = [], near_ts[0], near_ts[0]
    for t in near_ts[1:]:
        if t == prev + 1:
            prev = t
            continue
        out.append((start, prev))
        start = prev = t
    out.append((start, prev))
    return out


def intervals(rows: list[dict], near: float, sampled_fps: float) -> list[float]:
    """연속한 두 에피소드의 시작 프레임 차이 — 30fps 환산.

    🔴 **사이에 공이 안 잡힌 프레임이 하나라도 있으면 버린다.** 추적 끊김을
    「간격이 길다」로 읽으면 분포가 위로 늘어난다(사전 등록 「정의」).
    """
    seen = {r["t"] for r in rows}
    eps = episodes(rows, near)
    scale = NORMALISE_FPS / sampled_fps if sampled_fps else 1.0
    out = []
    for (s0, e0), (s1, _e1) in zip(eps, eps[1:]):
        if any(t not in seen for t in range(e0 + 1, s1)):
            continue            # 추적이 끊긴 구간을 건넌다 — 안 센다
        out.append((s1 - s0) * scale)
    return out


def quartiles(v: list[float]) -> tuple[float, float, float]:
    s = sorted(v)
    if len(s) < 4:
        m = statistics.median(s)
        return m, m, m
    q = statistics.quantiles(s, n=4, method="inclusive")
    return q[0], q[1], q[2]


def scan(clips: list[Path], label: str, device: str, detector_pair) -> dict:
    """한 표본을 훑는다. 클립마다 검출 → `analyse` → 에피소드·간격."""
    print(f"\n=== {label} — {len(clips)}편 ===", flush=True)
    per_near: dict[float, list[float]] = {n: [] for n in NEAR_SWEEP}
    kept, gated, unusable = 0, 0, 0
    clip_rows = []
    for i, clip in enumerate(clips, 1):
        t0 = time.time()
        try:
            det = detect_clip(clip, detector_pair, device)
            res = analyse(det)
        except Exception as exc:                        # noqa: BLE001
            print(f"  [{i}/{len(clips)}] {clip.name[:44]} — 🔴 {type(exc).__name__}: {exc}")
            unusable += 1
            continue
        if res is None or res.get("skipped") or "rows" not in res:
            unusable += 1
            print(f"  [{i}/{len(clips)}] {clip.name[:44]} — 건너뜀"
                  f" ({(res or {}).get('skipped', '사람 없음')})")
            continue
        if res["ball_coverage"] < MIN_BALL_COVERAGE:
            gated += 1
            print(f"  [{i}/{len(clips)}] {clip.name[:44]} — 공 추적 "
                  f"{res['ball_coverage']:.0%} < {MIN_BALL_COVERAGE:.0%} 제외")
            continue
        kept += 1
        fps = det["sampled_fps"]
        row = {"clip": clip.name, "frames": det["frames"], "sampled_fps": fps,
               "ball_coverage": res["ball_coverage"]}
        for n in NEAR_SWEEP:
            iv = intervals(res["rows"], n, fps)
            per_near[n].extend(iv)
            row[f"n_intervals@{n}"] = len(iv)
            row[f"n_episodes@{n}"] = len(episodes(res["rows"], n))
        clip_rows.append(row)
        print(f"  [{i}/{len(clips)}] {clip.name[:44]} — 에피소드 "
              f"{row[f'n_episodes@{NEAR}']} · 간격 {row[f'n_intervals@{NEAR}']}"
              f" ({time.time() - t0:.1f}s)", flush=True)
    return {"label": label, "clips_total": len(clips), "kept": kept,
            "gated_out": gated, "unusable": unusable,
            "per_near": {str(k): v for k, v in per_near.items()},
            "clip_rows": clip_rows}


def report(res: dict) -> None:
    print(f"\n--- {res['label']} ---")
    print(f"  클립 {res['clips_total']}편 · 잰 것 {res['kept']}"
          f" · 공 추적 미달 {res['gated_out']} · 못 잼 {res['unusable']}")
    for n in NEAR_SWEEP:
        v = res["per_near"][str(n)]
        if not v:
            print(f"  NEAR={n}: 간격 0개")
            continue
        q1, med, q3 = quartiles(v)
        inside = q1 <= ASSUMED[0] and ASSUMED[1] <= q3
        print(f"  NEAR={n}: 간격 {len(v):4d}개 · 중앙 {med:6.1f} "
              f"· Q1~Q3 {q1:.1f}~{q3:.1f} · 10~15 가 사분위 안: "
              f"{'예' if inside else '아니오'}")


def main() -> None:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    detector_pair = _load_detector(device)
    print(f"device={device} · NEAR={NEAR} · NEAR_SWEEP={NEAR_SWEEP} "
          f"· MIN_BALL_COVERAGE={MIN_BALL_COVERAGE} · 관문 A={MIN_INTERVALS}")

    soccernet = sorted(paths.soccernet_clips_root().glob("*.mp4"))
    if not soccernet:
        raise SystemExit(f"🔴 클립이 없다: {paths.soccernet_clips_root()}")
    main_res = scan(soccernet, "SoccerNet 방송", device, detector_pair)

    # 짝 기준 E — 드리블이 없는 표본. A 와 독립이라 언제나 돈다.
    control_clips = sorted((paths.external_root() / "clips").rglob("*.mp4"))
    control_res = (scan(control_clips, "야구 39편 (대조군)", device, detector_pair)
                   if control_clips else
                   {"label": "야구 39편 (대조군)", "clips_total": 0, "kept": 0,
                    "gated_out": 0, "unusable": 0,
                    "per_near": {str(n): [] for n in NEAR_SWEEP}, "clip_rows": []})

    report(main_res)
    report(control_res)

    primary = main_res["per_near"][str(NEAR)]
    control = control_res["per_near"][str(NEAR)]
    print("\n=== 판정 ===")
    print(f"  A (표본 ≥ {MIN_INTERVALS}): {len(primary)}개 → "
          f"{'통과' if len(primary) >= MIN_INTERVALS else '🔴 판별불가'}")
    print(f"  E (대조군 < {CONTROL_MAX}): {len(control)}개 → "
          f"{'통과' if len(control) < CONTROL_MAX else '🔴 계기가 딴 것을 센다'}")
    if len(primary) >= MIN_INTERVALS:
        q1, med, q3 = quartiles(primary)
        inside = q1 <= ASSUMED[0] and ASSUMED[1] <= q3
        flips = {n: (lambda v: (quartiles(v)[0] <= ASSUMED[0] <= ASSUMED[1] <= quartiles(v)[2])
                     if v else None)(main_res["per_near"][str(n)]) for n in NEAR_SWEEP}
        print(f"  B 중앙 {med:.1f} · Q1~Q3 {q1:.1f}~{q3:.1f} (30fps 환산)")
        print(f"  C 10~15 가 사분위 안: {'예' if inside else '🔴 아니오'}")
        print(f"  D 민감도 {flips} → "
              f"{'뒤집히지 않음' if len(set(v for v in flips.values() if v is not None)) <= 1 else '🔴 뒤집힘'}")

    out = {"main": main_res, "control": control_res,
           "constants": {"NEAR": NEAR, "NEAR_SWEEP": list(NEAR_SWEEP),
                         "MIN_BALL_COVERAGE": MIN_BALL_COVERAGE,
                         "MIN_INTERVALS": MIN_INTERVALS,
                         "CONTROL_MAX": CONTROL_MAX, "ASSUMED": list(ASSUMED),
                         "NORMALISE_FPS": NORMALISE_FPS}}
    (HERE / "interval_raw.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {HERE.name}/interval_raw.json")


if __name__ == "__main__":
    main()
