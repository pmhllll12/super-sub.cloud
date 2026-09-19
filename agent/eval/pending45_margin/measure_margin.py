"""미결 `ho` 45번 6회차 — 바깥이 짚은 자리가 **얼마나 어긋나는가**.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **돌리기 전에**
고정했다(커밋 `1446d5c3`). 여기서 고치지 않는다.

🔴 **조사 회차다** — production 을 **import 만** 한다. `src/` 0줄.

🔴 **바깥의 규칙은 1회차에서 import 한다** — `CONTACT_MAX`·`MIN_GAP`·
`MIN_BALL_COVERAGE` 와 `ball_foot_distance`·`find_touches`. 베끼면 갈라지고,
그러면 이 회차의 `δ` 가 1회차가 말한 그 바깥의 `δ` 가 아니게 된다.

🔴 **GPU 를 안 쓴다.** 52번 2회차가 뜬 축구 포즈 캐시를 읽는다
(`paths.motion_id_cache()`). 🔴 **52번을 다시 여는 것이 아니다** — 보류된
항목의 **이미 뜬 자산만** 읽는다.

    uv run python eval/pending45_margin/measure_margin.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending45_touch_events"))

import paths  # noqa: E402
from supersub_agent import features as F  # noqa: E402

# 🔴 1회차의 규칙과 상수를 그대로 쓴다. 새 상수 0개(사전 등록 F).
from measure_touches import (  # noqa: E402
    CONTACT_MAX,
    MIN_BALL_COVERAGE,
    MIN_GAP,
    ball_foot_distance,
    find_touches,
)

#: 사전 등록이 정한 여백 격자 (M2 용). 판정에 안 쓴다 — 확인용이다.
MARGINS = (2, 3, 5, 8, 12, 20)

#: 무작위 대조군. 시드와 반복수는 사전 등록에 박았다.
SEED = 20260918
TRIALS = 200


def clips():
    """(동작, 클립 id, 키포인트, 공, error) — 캐시 사본에서만 읽는다."""
    root = paths.motion_id_cache()
    for motion in sorted(p.name for p in root.iterdir() if p.is_dir()):
        for npz in sorted((root / motion).glob("*.npz")):
            d = np.load(npz, allow_pickle=True)
            yield motion, npz.stem, d["keypoints"], d["ball"], str(d["error"])


def outcome(kps, chain, limb, event, window):
    """한 번의 `segment_phases` 결과를 사유로 남긴다 (5회차와 같은 분류).

    🔴 5회차가 문구 셋 중 둘만 알아 `other` 6건을 냈다. 세 번째 문구를 더했다.
    """
    try:
        ph = F.segment_phases(kps, chain, limb=limb, event=event, window=window)
        return "ok", ph.impact
    except F.InsufficientQuality as exc:
        msg = str(exc)
        if "분석 가능한 프레임이 없다" in msg or "산출할 수 있는 프레임이 없다" in msg:
            return "empty", None
        if "경계에 있음" in msg:
            return "boundary", None
        return "other:InsufficientQuality", None
    except Exception as exc:  # noqa: BLE001 — 어떤 실패였는지가 결과다
        return f"other:{type(exc).__name__}", None


def usable_mask(kps, chain, limb):
    """`segment_phases` 가 보는 `usable`. production 규칙 그대로."""
    series = F.chain_series(kps, chain)
    return F.valid_frames(kps, limb, chain) & np.isfinite(series)


def main() -> int:
    gates = {"전체": 0, "①error": 0, "②quality": 0, "③event": 0,
             "④ball": 0, "⑤touch": 0, "통과": 0}
    kept, dropped, checks_a, m2 = [], [], [], []
    rng = np.random.default_rng(SEED)

    for motion, clip, kps, ball, err in clips():
        gates["전체"] += 1
        tag = {"motion": motion, "clip": clip}

        if err:
            gates["①error"] += 1
            dropped.append({**tag, "gate": "①error", "detail": err})
            continue
        try:
            F.check_quality(kps, limb="leg", side="auto")
        except Exception as exc:  # noqa: BLE001
            gates["②quality"] += 1
            dropped.append({**tag, "gate": "②quality", "detail": type(exc).__name__})
            continue

        norm = F.normalize(kps)
        chain, _ = F.identify_limb(norm, "leg", "auto")
        base_reason, e = outcome(norm, chain, "leg", "extension_peak", None)
        if base_reason != "ok":
            gates["③event"] += 1
            dropped.append({**tag, "gate": "③event", "detail": base_reason})
            continue

        if ball.shape[0] != kps.shape[0]:
            coverage = 0.0
        else:
            coverage = float((ball[:, 2] > 0).mean())
        if coverage < MIN_BALL_COVERAGE:
            gates["④ball"] += 1
            dropped.append({**tag, "gate": "④ball", "detail": round(coverage, 4)})
            continue

        dist = ball_foot_distance(kps, ball)
        touches = find_touches(dist)
        if not touches:
            gates["⑤touch"] += 1
            dropped.append({**tag, "gate": "⑤touch", "detail": "후보 0"})
            continue

        gates["통과"] += 1
        usable = usable_mask(norm, chain, "leg")
        first = int(np.argmax(usable))
        last = int(len(usable) - 1 - np.argmax(usable[::-1]))

        # M1 — e 에 가장 가까운 터치 후보
        d = min(touches, key=lambda t: abs(t - e))
        delta = int(d - e)

        # 무작위 대조군 — 같은 구간에 같은 개수를 뿌려 e 까지의 최단 거리
        span = np.arange(first, last + 1)
        null = []
        for _ in range(TRIALS):
            pick = rng.choice(span, size=min(len(touches), len(span)), replace=False)
            null.append(int(np.abs(pick - e).min()))

        kept.append({
            **tag, "e": int(e), "d": int(d), "delta": delta,
            "abs_delta": abs(delta), "n_touches": len(touches),
            "coverage": round(coverage, 4),
            "first": first, "last": last, "frames": int(len(kps)),
            "null_median": float(statistics.median(null)),
            "null_mean": round(float(np.mean(null)), 3),
        })

        # A(계기) + M2 — 여백 격자
        for m in MARGINS:
            a, b = d - m, d + m + 1
            reason, impact = outcome(norm, chain, "leg", "extension_peak", (a, b))
            sub = usable[max(0, a):max(0, b)]
            if sub.any():
                w_first = max(0, a) + int(np.argmax(sub))
                w_last = max(0, a) + len(sub) - 1 - int(np.argmax(sub[::-1]))
            else:
                w_first = w_last = None
            m2.append({**tag, "m": m, "a": a, "b": b, "reason": reason,
                       "impact": impact,
                       "pull_front": None if w_first is None else w_first - a,
                       "pull_back": None if w_last is None else (b - 1) - w_last})
            # ㉠ — 창이 e 를 담고 양 끝에서 2 이상이면 창 안 argmax == e 여야 한다
            if a <= e < b and e - max(a, w_first if w_first is not None else a) >= 2 \
               and (min(b - 1, w_last if w_last is not None else b - 1)) - e >= 2:
                checks_a.append({**tag, "m": m,
                                 "ok": reason == "ok" and impact == e,
                                 "reason": reason, "impact": impact, "e": int(e)})

    out = {"gates": gates, "kept": kept, "dropped": dropped,
           "checks_a": checks_a, "m2": m2}
    (HERE / "margin_raw.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    report(out)
    return 0


def report(out) -> None:
    gates, kept, checks_a, m2 = out["gates"], out["kept"], out["checks_a"], out["m2"]

    print("관문 — 분모")
    for k, v in gates.items():
        print(f"  {k:<10} {v}")

    bad = [c for c in checks_a if not c["ok"]]
    print(f"\n[A 계기] ㉠ 부분집합 argmax : 위반 {len(bad)} / {len(checks_a)}")
    for b in bad[:5]:
        print("   ", b)

    others = [r for r in m2 if r["reason"].startswith("other")]
    print(f"[B 계기] 분류 안 된 실패(other) : {len(others)} / {len(m2)}")
    for o in others[:5]:
        print("   ", o)

    if len(kept) < 10:
        print(f"\n🔴 [D 짝 기준] 관문 통과 {len(kept)}편 < 10 — "
              "분위수를 내지 않는다. 판별불가.")
        return

    ad = sorted(k["abs_delta"] for k in kept)
    nulls = sorted(k["null_median"] for k in kept)
    print(f"\n[M1] n={len(kept)}")
    print(f"  |δ|      중앙 {statistics.median(ad):.1f} · "
          f"평균 {statistics.mean(ad):.1f} · 범위 {ad[0]}~{ad[-1]}")
    print(f"  무작위   중앙 {statistics.median(nulls):.1f} · "
          f"평균 {statistics.mean(nulls):.1f}")
    print(f"[C] 실제 < 무작위 : "
          f"{'✅' if statistics.median(ad) < statistics.median(nulls) else '🔴'}")

    print(f"\n[E · P1] |δ| 중앙 > 5 : "
          f"{'참' if statistics.median(ad) > 5 else '거짓'} "
          f"(중앙 {statistics.median(ad):.1f})")

    def q(v, p):
        i = min(len(v) - 1, int(round(p * (len(v) - 1))))
        return v[i]

    print("\n[산수 따라 나온 값] 필요한 여백 m* = |δ| 분위수 + 2")
    for p in (0.5, 0.8, 0.9, 1.0):
        print(f"  {p:.0%} 커버 : |δ| {q(ad, p):>3} → m* {q(ad, p) + 2:>3}")

    print("\n[M2] 창 안 검출 실패로 경계가 안쪽으로 당겨진 정도")
    print(f"{'m':>4} | {'n':>4} | {'당겨진 창':>9} | {'앞 중앙':>7} | {'뒤 중앙':>7} | {'ok':>6}")
    for m in MARGINS:
        sub = [r for r in m2 if r["m"] == m]
        pulled = [r for r in sub
                  if (r["pull_front"] or 0) > 0 or (r["pull_back"] or 0) > 0]
        pf = [r["pull_front"] for r in sub if r["pull_front"]]
        pb = [r["pull_back"] for r in sub if r["pull_back"]]
        okr = sum(r["reason"] == "ok" for r in sub) / len(sub)
        print(f"{m:>4} | {len(sub):>4} | {len(pulled) / len(sub):8.1%} | "
              f"{statistics.median(pf) if pf else 0:7.1f} | "
              f"{statistics.median(pb) if pb else 0:7.1f} | {okr:6.1%}")
    allp = [r for r in m2 if (r["pull_front"] or 0) > 0 or (r["pull_back"] or 0) > 0]
    print(f"[E · P3] 당겨진 창 {len(allp)}/{len(m2)} = {len(allp) / len(m2):.1%} "
          f"({'≥20% 참' if len(allp) / len(m2) >= 0.20 else '≥20% 거짓'})")

    print("\n[D 짝 기준] 클립별 δ — 큰 쪽부터")
    for k in sorted(kept, key=lambda r: -r["abs_delta"]):
        print(f"    {k['motion']:<12} {k['clip']:<14} δ={k['delta']:>+5} "
              f"후보 {k['n_touches']:>2} · 공 {k['coverage']:.2f} · "
              f"무작위중앙 {k['null_median']:.0f}")
    trimmed = sorted(kept, key=lambda r: -r["abs_delta"])[2:]
    ta = statistics.median([k["abs_delta"] for k in trimmed])
    tn = statistics.median([k["null_median"] for k in trimmed])
    print(f"\n[D] 가장 큰 2편을 빼고: |δ| 중앙 {ta:.1f} · 무작위 {tn:.1f} → "
          f"C {'유지' if ta < tn else '🔴 안 유지'}")


if __name__ == "__main__":
    raise SystemExit(main())
