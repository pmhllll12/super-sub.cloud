"""미결 `ho` 45번 7회차 — 바깥이 **가리키기는 하는가**, 클립별로.

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **돌리기 전에**
고정했다(커밋 `dd0b043a`). 여기서 고치지 않는다.

🔴 **새 측정을 하지 않는다.** 6회차가 뜬 원자료
(`eval/pending45_margin/margin_raw.json`)를 **올바른 단위로 다시 요약**할
뿐이다 — 포즈도 공도 다시 안 읽는다. `src/` 0줄.

    uv run python eval/pending45_pointing/measure_pointing.py
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "pending45_margin" / "margin_raw.json"

# 🔴 사전 등록이 정한 값. 판정 문턱이 아니라 정밀도·재현성 값이다.
SEED = 20260918
TRIALS = 2000
SHAM_REPS = 500

#: 사전 등록이 정한 층. 🔴 **보고만 하고 판정에 안 쓴다** (사후를 사전으로
#: 올린 것이라 순환이고, 분모가 전부 한 자릿수다).
STRATA = (("후보 ≤5", lambda n: n <= 5),
          ("후보 6~9", lambda n: 6 <= n <= 9),
          ("후보 ≥10", lambda n: n >= 10))


def null_sample(rng, first, last, k, trials):
    """그 클립의 귀무 분포 — 유효 구간에 후보 k개를 무작위로 놓았을 때
    `e` 까지의 최단 거리. 6회차가 쓴 것과 **같은 구성**이다."""
    span = np.arange(first, last + 1)
    k = min(k, len(span))
    out = np.empty(trials, dtype=np.int64)
    for i in range(trials):
        pick = rng.choice(span, size=k, replace=False)
        out[i] = int(np.abs(pick - E_HOLDER[0]).min())
    return out


E_HOLDER = [0]  # null_sample 이 쓰는 e. 루프마다 갈아 끼운다.


def midp(null: np.ndarray, obs: int) -> float:
    """중간 순위 분위 — `P(null < obs) + 0.5 * P(null == obs)`.

    🔴 `P(null <= obs)` 를 쓰면 null 이 이산이라 귀무 아래에서도 0.5 가 안 된다.
    사전 등록이 이 보정을 적어 두었고, 기준 A 가 실제로 먹는지 확인한다.
    """
    return float((null < obs).mean() + 0.5 * (null == obs).mean())


def main() -> int:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    kept, gates = raw["kept"], raw["gates"]

    digest = hashlib.sha256(RAW.read_bytes()).hexdigest()[:16]
    print(f"[B 계기] 6회차 원자료 그대로 — {RAW.name} sha256:{digest}")
    print(f"          관문 {gates} · 통과 {len(kept)}편")

    rng_null = np.random.default_rng(SEED)
    rng_sham = np.random.default_rng(SEED + 1)

    rows, shams = [], []
    for c in kept:
        E_HOLDER[0] = c["e"]
        null = null_sample(rng_null, c["first"], c["last"], c["n_touches"], TRIALS)
        pct = midp(null, c["abs_delta"])

        # A(계기) — 가짜 바깥. 같은 귀무 과정에서 뽑은 관측의 분위는 0.5 여야 한다.
        sham = null_sample(rng_sham, c["first"], c["last"], c["n_touches"], SHAM_REPS)
        sham_pcts = [midp(null, int(s)) for s in sham]
        shams.append(statistics.mean(sham_pcts))

        rows.append({"motion": c["motion"], "clip": c["clip"],
                     "delta": c["delta"], "abs_delta": c["abs_delta"],
                     "n_touches": c["n_touches"], "pct": round(pct, 4),
                     "null_median": float(np.median(null)),
                     "sham_mean": round(statistics.mean(sham_pcts), 4)})

    (HERE / "pointing.json").write_text(
        json.dumps({"rows": rows, "raw_sha256_16": digest,
                    "seed": SEED, "trials": TRIALS, "sham_reps": SHAM_REPS},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    report(rows, shams)
    return 0


def report(rows, shams) -> None:
    sham_mean = statistics.mean(shams)
    ok_a = abs(sham_mean - 0.5) <= 0.10
    print(f"\n[A 계기] 가짜 바깥의 평균 분위 = {sham_mean:.3f} "
          f"(합격 0.5 ± 0.10) → {'✅ 교정됨' if ok_a else '🔴 계기 고장'}")
    if not ok_a:
        print("🔴 사전 등록대로 판정을 내지 않는다.")
        return

    pcts = [r["pct"] for r in rows]
    mean_pct = statistics.mean(pcts)
    print(f"\n[C] 실제 바깥의 평균 분위 = {mean_pct:.3f} (합격선 ≤ 0.35) → "
          f"{'✅ 가리킨다' if mean_pct <= 0.35 else '🔴 안 선다'}")
    print(f"    중앙 {statistics.median(pcts):.3f} · "
          f"범위 {min(pcts):.3f}~{max(pcts):.3f} · n={len(pcts)}")

    low = [r for r in rows if r["pct"] <= 0.10]
    print(f"[D] 분위 ≤ 0.10 인 클립 {len(low)}편 (귀무 기댓값 1.7)")

    print("\n[E] 층별 — 🔴 보고만 한다 (판정에 안 쓴다, 분모가 한 자릿수)")
    for name, pred in STRATA:
        g = [r for r in rows if pred(r["n_touches"])]
        if not g:
            print(f"    {name:<8} 0편")
            continue
        print(f"    {name:<8} n={len(g):>2} 평균 분위 "
              f"{statistics.mean(r['pct'] for r in g):.3f} · "
              f"≤0.10 {sum(r['pct'] <= 0.10 for r in g)}편")

    print("\n클립별 — 분위가 낮은 쪽부터")
    print(f"{'동작':<12} {'클립':<14} {'δ':>6} {'후보':>4} {'분위':>7} {'null중앙':>8}")
    for r in sorted(rows, key=lambda x: x["pct"]):
        print(f"{r['motion']:<12} {r['clip']:<14} {r['delta']:>+6} "
              f"{r['n_touches']:>4} {r['pct']:>7.3f} {r['null_median']:>8.0f}")


if __name__ == "__main__":
    raise SystemExit(main())
