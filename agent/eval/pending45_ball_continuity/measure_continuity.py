"""공 궤적에 연속성을 걸면 이벤트가 깨끗해지는가 — 3회차 (미결 `ho` 45번 ㉲-a).

🔴 **사전 등록(`PREREGISTRATION.md`, 커밋 `818179b`)을 먼저 읽는다.**
상수와 합격선은 이 파일을 쓰기 전에 굳혔고 결과를 보고 고치지 않는다.

🔴 **GPU 를 안 쓴다.** 2회차가 남긴 `ball_tracks.npz` 를 읽어 **같은 궤적에
규칙만 바꿔 댄다** — 두 회차의 차이가 순수하게 규칙 차이가 된다.

🔴 **`src/` 를 한 줄도 안 고친다.**

    cd agent && uv run python eval/pending45_ball_continuity/measure_continuity.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "pending45_ball_events"

# 🔴 사전 등록에서 박은 값. **결과를 보고 돌리지 않는다.**
MAX_BALL_SPEED = 4.0       # 어깨너비 / 프레임 — 프로 강슛 35m/s ≈ 3.6 에 여유
MIN_ACCEL = 1.0            # 🔴 2회차와 **같은 값**
MIN_GAP = 8                # 1·2회차와 같다
MIN_BALL_COVERAGE = 0.30
IMPLAUSIBLE_ACCEL = MAX_BALL_SPEED * 2   # 기준 E


def pixel_accel_max(ball: np.ndarray) -> float | None:
    """픽셀 기준 최대 가속 — `scale` 역산에만 쓴다."""
    p, seen, n = ball[:, :2], ball[:, 2] > 0, len(ball)
    best = None
    for t in range(1, n - 1):
        if seen[t - 1] and seen[t] and seen[t + 1]:
            a = float(np.hypot(*((p[t + 1] - p[t]) - (p[t] - p[t - 1]))))
            best = a if best is None else max(best, a)
    return best


def gate_by_speed(ball: np.ndarray, scale: float) -> tuple[np.ndarray, int]:
    """물리적으로 닿을 수 없는 위치를 **미검출로 본다**. (걸러진 궤적, 버린 수)

    🔴 **속도 상한이지 가속 상한이 아니다.** 공은 빠를 수 있지만 상한이 있다.
    🔴 **간격으로 나눈다** — 몇 프레임 안 보이다 돌아온 정상 복귀를
       텔레포트로 오인하지 않게.
    """
    out = ball.copy()
    last_t, dropped = None, 0
    for t in range(len(out)):
        if out[t, 2] <= 0:
            continue
        if last_t is None:
            last_t = t
            continue
        step = (np.hypot(*(out[t, :2] - out[last_t, :2])) / scale) / (t - last_t)
        if step > MAX_BALL_SPEED:
            out[t, 2] = 0.0          # 미검출로 본다 (이어 붙이지 않는다)
            dropped += 1
        else:
            last_t = t
    return out, dropped


def ball_accel(ball: np.ndarray, scale: float) -> np.ndarray:
    """2회차와 **같은 규칙**. 복제가 아니라 같은 산술을 그대로 옮긴 것이다."""
    p, seen, n = ball[:, :2] / scale, ball[:, 2] > 0, len(ball)
    accel = np.full(n, np.nan)
    for t in range(1, n - 1):
        if seen[t - 1] and seen[t] and seen[t + 1]:
            accel[t] = float(np.hypot(*((p[t + 1] - p[t]) - (p[t] - p[t - 1]))))
    return accel


def find_events(accel: np.ndarray) -> list[int]:
    """2회차와 **같은 규칙**."""
    cand = []
    for t in range(len(accel)):
        a = accel[t]
        if not np.isfinite(a) or a < MIN_ACCEL:
            continue
        prev = accel[t - 1] if t > 0 and np.isfinite(accel[t - 1]) else -np.inf
        nxt = accel[t + 1] if t + 1 < len(accel) and np.isfinite(accel[t + 1]) else -np.inf
        if a >= prev and a >= nxt:
            cand.append(t)
    kept = []
    for t in sorted(cand, key=lambda i: -accel[i]):
        if all(abs(t - k) >= MIN_GAP for k in kept):
            kept.append(t)
    return sorted(kept)


def main() -> None:
    tracks = np.load(PREV / "ball_tracks.npz")
    prev = {r["clip"]: r for r in json.loads(
        (PREV / "events_raw.json").read_text(encoding="utf-8"))}
    print(f"2회차 궤적 {len(tracks.files)}편 · MAX_BALL_SPEED={MAX_BALL_SPEED} "
          f"MIN_ACCEL={MIN_ACCEL} (GPU 미사용)\n")

    # ── 기준 G — 게이트 OFF 에서 2회차가 재현되는가 ────────────────────
    print("── 기준 G: 게이트 OFF 재현 (역산한 scale 이 맞는지 먼저 본다)")
    scales, mismatch = {}, []
    for name in tracks.files:
        rec = prev.get(name) or {}
        ref_max, ref_events = rec.get("accel_max"), rec.get("events")
        px = pixel_accel_max(tracks[name])
        if not ref_max or px is None:
            continue
        scales[name] = px / ref_max
        got = find_events(ball_accel(tracks[name], scales[name]))
        if got != ref_events:
            mismatch.append((name, ref_events, got))
    print(f"  scale 역산 {len(scales)}편 · 이벤트 목록 불일치 {len(mismatch)}편 "
          f"{'✅' if not mismatch else '🔴'}")
    for name, ref, got in mismatch[:5]:
        print(f"    🔴 {name[:30]:30s} 2회차 {ref} → 재현 {got}")
    if mismatch:
        print("\n🔴 **G 가 안 섰다. A·B·E·F 를 읽지 않는다** (사전 등록).")
        print("   역산이 틀렸다는 뜻이므로 GPU 로 궤적과 scale 을 다시 뽑을 것.")
        return
    print("  → G 통과. 아래를 읽어도 된다.\n")

    # ── 게이트 ON ──────────────────────────────────────────────────────
    rows = []
    for name in sorted(tracks.files):
        if name not in scales:
            continue
        ball, scale = tracks[name], scales[name]
        n_seen_before = int((ball[:, 2] > 0).sum())
        gated, dropped = gate_by_speed(ball, scale)
        accel = ball_accel(gated, scale)
        events = find_events(accel)
        rows.append({
            "clip": name,
            "scale_px": round(scale, 2),
            "coverage_before": round(n_seen_before / len(ball), 3),
            "coverage_after": round(float((gated[:, 2] > 0).mean()), 3),
            "dropped": dropped,
            "dropped_ratio": round(dropped / max(n_seen_before, 1), 3),
            "events_before": prev[name]["events"],
            "events": events,
            "n_events": len(events),
            "accel_at_events": [round(float(accel[t]), 3) for t in events],
            "accel_max": (round(float(np.nanmax(accel)), 3)
                          if np.isfinite(accel).any() else None),
        })
        print(f"  {name[:30]:30s} 이벤트 {len(prev[name]['events'])}→{len(events):<2d} "
              f"버림 {dropped:3d}({rows[-1]['dropped_ratio']:.0%}) "
              f"최대가속 {prev[name]['accel_max']}→{rows[-1]['accel_max']}")

    (HERE / "continuity_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [r for r in rows if r["coverage_before"] >= MIN_BALL_COVERAGE]
    dropped_clips = [r for r in rows if r not in ok]
    counts = [r["n_events"] for r in ok]
    found = sum(1 for c in counts if c >= 1) / len(counts)
    not_noisy = sum(1 for c in counts if c <= 2) / len(counts)
    implausible = [r for r in ok for a in r["accel_at_events"]
                   if a >= IMPLAUSIBLE_ACCEL]
    gutted = [r for r in ok if r["dropped_ratio"] >= 0.5]

    print("\n" + "=" * 70)
    print(f"분모 {len(ok)}/{len(rows)} 편 · 이벤트 수 분포 {sorted(counts)}")
    print("\n── 사전 등록 판정")
    print(f"  G 게이트 OFF 재현        : 불일치 0편 ✅")
    print(f"  A 1개 이상 찾음 ≥80%     : {found:.0%} {'✅' if found >= 0.8 else '🔴'}"
          f"   (2회차 78%)")
    print(f"  B 2개 이하     ≥80%     : {not_noisy:.0%} {'✅' if not_noisy >= 0.8 else '🔴'}"
          f"   (2회차 89%)")
    print(f"  E 남은 이벤트 가속 <{IMPLAUSIBLE_ACCEL} : 위반 {len(implausible)}건 "
          f"{'✅' if not implausible else '🔴'}")
    print(f"  F 절반 이상 버린 클립     : {len(gutted)}편 "
          f"{[r['clip'][:22] for r in gutted] or '없음'}")
    print(f"  C production 무수정      : ✅   D 뺀 클립: {len(dropped_clips)}편")

    print("\n── 사후 관찰 (판정에 안 쓴다)")
    tot_before = sum(r["coverage_before"] for r in ok) / len(ok)
    tot_after = sum(r["coverage_after"] for r in ok) / len(ok)
    print(f"  평균 공 커버리지 {tot_before:.0%} → {tot_after:.0%}")
    print("  🔴 커버리지가 **내려가는 것이 정상**이다 — 가짜 검출을 버렸으니.")
    print("     올라가면 게이트가 아무 일도 안 한 것이다.")
    worst = max(ok, key=lambda r: r["accel_max"] or 0)
    print(f"  게이트 후 최대가속: {worst['accel_max']} ({worst['clip'][:26]})")


if __name__ == "__main__":
    main()
