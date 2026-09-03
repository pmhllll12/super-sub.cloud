"""B-4 후속 — clean blind review 60건으로 A-pose vs B-pose를 실제로 검정한다.

`clean_review_analysis.py`는 Tier 0(7건)과 Tier 1(53건)을 **따로** 세는 데서
멈춘다. Tier 0는 A 3 : B 2, Tier 1은 B 24 : A 14로 방향이 반대라, 합칠 수
있는지와 Tier 1의 우세가 표본 선정에서 온 것인지를 따져야 결론이 난다.

여기서 확인하는 것:

 1. 두 층을 합친 전체 tally와 부호검정(정확 이항).
 2. **선정 편향** — Tier 1은 `info_score` 상위에서 뽑혔고 그 점수에는
    `b_locked`(가중치 2.0)와 `a_pose_switch`(1.0)가 들어 있다. 둘 다 A/B에
    대해 비대칭인 항이다. 표본과 모집단(불일치 596프레임)의 공변량 분포를
    비교하고, 층별로 나눠 우세가 어디서 오는지 본다.
 3. **클러스터** — 프레임은 클립당 최대 4건까지 들어 있다. 클립 단위로 묶어
    클러스터 부트스트랩 CI와 클립 단위 부호검정을 낸다.

읽기 전용이다. labels.json·selector·가중치·기존 산출물을 수정하지 않으며
clean review를 GT로 승격하지도 않는다.

⚠️ **import만으로는 아무것도 실행되지 않는다.** 산출물을 쓰는 코드는 전부
`main()` 안에 있고 `__main__` 가드로만 호출된다. 이 파일명이 pytest 기본
수집 패턴 `*_test.py`에 걸리기 때문이다 — 가드가 없으면 **수집 단계에서
모듈이 import되면서 실행되고**, `B4`(= /mnt/d/supersub-phaseA/eval_b4)의
산출물 5개를 조용히 덮어쓴다. 테스트는 그대로 통과하므로 신호도 없다.
`pyproject.toml`의 `[tool.pytest.ini_options] testpaths`로도 막아 두었지만,
설정은 실행 위치·인자에 따라 우회될 수 있으므로 가드가 최종 방어선이다.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/mnt/d/supersub-phaseA")
B4 = ROOT / "eval_b4"

SEED = 20260828
N_BOOT = 20000

TIER0_CASE = {  # clean_review_analysis.py 와 동일
    "T0-01": ("3USSmzO001k", 119), "T0-02": ("5-jBTNp5IQA", 75),
    "T0-03": ("IeDin6oB-IY", 75), "T0-04": ("N5zWQkoLM3M", 75),
    "T0-05": ("N5zWQkoLM3M", 119), "T0-06": ("X6dC9pu5H3k", 107),
    "T0-07": ("sYl2jCqsSKo", 119),
}


def outcome(label: str, a: int, b: int) -> str:
    if label in ("", "uncertain", "none"):
        return "excluded"
    v = int(label)
    if v == b:
        return "B"
    if v == a:
        return "A"
    return "neither"


# ---------------------------------------------------------------- 통계 도구
def binom_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """정확 이항 양측 p (같거나 더 극단인 확률의 합)."""
    if n == 0:
        return float("nan")
    pmf = [math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(n + 1)]
    thr = pmf[k] * (1 + 1e-9)
    return min(1.0, sum(v for v in pmf if v <= thr))


def tally(rs) -> tuple[int, int, int, int]:
    c = Counter(r["winner"] for r in rs)
    return c["A"], c["B"], c["neither"], c["excluded"]


def summarize(name: str, rs) -> dict:
    a, b, nei, exc = tally(rs)
    n = a + b
    return {
        "subset": name, "n_reviewed": len(rs), "a_wins": a, "b_wins": b,
        "neither": nei, "excluded": exc, "n_decided": n,
        "b_share": f"{b / n:.3f}" if n else "",
        "margin_b_minus_a": b - a,
        "p_two_sided": f"{binom_two_sided(b, n):.4f}" if n else "",
    }


def frac(rs, col) -> float:
    return sum(r[col] == "1" for r in rs) / len(rs)


# ---------------------------------------------------------------- 출력
def show(rs) -> None:
    for r in rs:
        print(f"  {r['subset']:<34} 판정 {r['n_decided']:>2}건  "
              f"A {r['a_wins']:>2} : B {r['b_wins']:>2}  "
              f"margin {r['margin_b_minus_a']:+d}  "
              f"B비율 {r['b_share'] or '-':>5}  p={r['p_two_sided'] or '-'}")


def main() -> None:
    # ---------------------------------------------------------------- 입력
    dis = {}
    for r in csv.DictReader(open(B4 / "ab_disagreement_frames.csv")):
        dis[(r["clip_id"], int(r["frame"]))] = r

    reviews = []  # (tier, case, clip_id, frame, label, confidence, note)
    for r in csv.DictReader(open(B4 / "tier0_ai_clean_blind_review.csv")):
        cid, f = TIER0_CASE[r["case"]]
        reviews.append(("T0", r["case"], cid, f, r["human_box_index"],
                        r["confidence"], r["human_note"]))
    for r in csv.DictReader(open(B4 / "tier1_ai_clean_blind_review.csv")):
        reviews.append(("T1", r["case"], r["clip_id"], int(r["frame"]),
                        r["human_box_index"], r["confidence"], r["human_note"]))

    rows = []
    for tier, case, cid, f, label, conf, note in reviews:
        d = dis[(cid, f)]
        a, b = int(d["a_pose_box"]), int(d["b_pose_box"])
        rows.append({
            "tier": tier, "case": case, "clip_id": cid, "frame": f,
            "clean_label": label, "confidence": conf,
            "a_pose_box": a, "b_pose_box": b,
            "winner": outcome(label, a, b),
            "b_locked": d["b_locked"], "a_pose_switch": d["a_pose_switch"],
            "run_len": d["run_len"], "info_score": d["info_score"],
            "min_box_frac": d["min_box_frac"], "n_candidates": d["n_candidates"],
            "note": note,
        })

    decided = [r for r in rows if r["winner"] in ("A", "B")]

    with open(B4 / "clean_review_ab_frames.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # ---------------------------------------------------------------- 1. 전체·층별
    subsets = [
        ("전체 (Tier 0 + Tier 1)", rows),
        ("Tier 0 (GT 있던 7건)", [r for r in rows if r["tier"] == "T0"]),
        ("Tier 1 (신규 53건)", [r for r in rows if r["tier"] == "T1"]),
        ("confidence=high 만", [r for r in rows if r["confidence"] == "high"]),
        ("confidence=high+medium", [r for r in rows if r["confidence"] in ("high", "medium")]),
    ]
    main_rows = [summarize(n, rs) for n, rs in subsets]

    # ---------------------------------------------------------------- 2. 선정 편향
    strata = [
        ("a_pose_switch=1 (A가 방금 이탈)", lambda r: r["a_pose_switch"] == "1"),
        ("a_pose_switch=0", lambda r: r["a_pose_switch"] == "0"),
        ("b_locked=1 (B 고착)", lambda r: r["b_locked"] == "1"),
        ("b_locked=0", lambda r: r["b_locked"] == "0"),
        ("비대칭항 둘 다 0 (중립 표본)",
         lambda r: r["a_pose_switch"] == "0" and r["b_locked"] == "0"),
    ]
    strat_rows = [summarize(n, [r for r in rows if fn(r)]) for n, fn in strata]

    # 표본 vs 모집단 공변량 분포 — 모집단은 프레임 전수와 run 대표 두 가지로 본다
    pop_frames = list(dis.values())
    run_start: dict[tuple[str, int], int] = {}
    by_clip = defaultdict(list)
    for r in pop_frames:
        by_clip[r["clip_id"]].append(int(r["frame"]))
    for cid, fs in by_clip.items():
        prev, start = None, None
        for f in sorted(fs):
            if prev is None or f != prev + 1:
                start = f
            run_start[(cid, f)] = start
            prev = f
    # run 대표는 **run의 중앙 프레임**으로 잡는다. 중립적인 기준이 필요해서다 —
    # ab_disagreement_frames.csv는 info_score 내림차순이라 등장 순서로 대표를 뽑으면
    # 비교하려는 편향이 모집단 쪽에도 섞이고, run 시작 프레임으로 뽑으면 run이
    # 시작되는 이유 자체가 대개 A의 이탈이라 a_pose_switch가 0.93까지 올라간다.
    _runs = defaultdict(list)
    for r in pop_frames:
        _runs[(r["clip_id"], run_start[(r["clip_id"], int(r["frame"]))])].append(r)
    pop_runs = {k: sorted(v, key=lambda r: int(r["frame"]))[len(v) // 2]
                for k, v in _runs.items()}

    cov_rows = []
    for col in ("b_locked", "a_pose_switch"):
        cov_rows.append({
            "covariate": col,
            "population_frames": f"{frac(pop_frames, col):.3f}",
            "population_runs": f"{frac(list(pop_runs.values()), col):.3f}",
            "reviewed_sample": f"{frac(rows, col):.3f}",
            "decided_sample": f"{frac(decided, col):.3f}",
            "info_score_weight": {"b_locked": 2.0, "a_pose_switch": 1.0}[col],
        })

    # ---------------------------------------------------------------- 3. 클러스터
    clip_rows = []
    for cid in sorted({r["clip_id"] for r in rows}):
        rs = [r for r in rows if r["clip_id"] == cid]
        a, b, nei, exc = tally(rs)
        clip_rows.append({"clip_id": cid, "n_reviewed": len(rs), "a_wins": a,
                          "b_wins": b, "neither": nei, "excluded": exc,
                          "margin_b_minus_a": b - a,
                          "clip_verdict": "B" if b > a else ("A" if a > b else "tie")})

    # 클립 안에서 승패가 갈리는가, 몰리는가. 몰린다면 "어느 selector가 나은가"보다
    # "어떤 클립에서 continuity가 도움이 되는가"가 실제 질문이 된다.
    decided_clips = [c for c in clip_rows if c["a_wins"] + c["b_wins"] > 0]
    unanimous = [c for c in decided_clips if c["a_wins"] == 0 or c["b_wins"] == 0]
    multi = [c for c in decided_clips if c["a_wins"] + c["b_wins"] >= 2]
    multi_unanimous = [c for c in multi if c["a_wins"] == 0 or c["b_wins"] == 0]

    clip_verdicts = Counter(c["clip_verdict"] for c in clip_rows)
    cb, ca = clip_verdicts["B"], clip_verdicts["A"]
    clip_sign_p = binom_two_sided(cb, cb + ca)

    # 클러스터 부트스트랩 — 클립을 복원추출해 b_share의 CI
    rng = random.Random(SEED)
    clips = sorted({r["clip_id"] for r in decided})
    per_clip = {c: [r for r in decided if r["clip_id"] == c] for c in clips}
    boot = []
    for _ in range(N_BOOT):
        pick = [rng.choice(clips) for _ in clips]
        a = b = 0
        for c in pick:
            for r in per_clip[c]:
                a += r["winner"] == "A"
                b += r["winner"] == "B"
        if a + b:
            boot.append(b / (a + b))
    boot.sort()
    lo, hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot)) - 1]

    a_all, b_all, _, _ = tally(rows)
    n_all = a_all + b_all

    with open(B4 / "clean_review_ab_test.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(main_rows[0]))
        w.writeheader()
        w.writerows(main_rows)
        w.writerows(strat_rows)
    with open(B4 / "clean_review_ab_by_clip.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(clip_rows[0]))
        w.writeheader()
        w.writerows(clip_rows)
    with open(B4 / "clean_review_ab_covariates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cov_rows[0]))
        w.writeheader()
        w.writerows(cov_rows)

    # ---------------------------------------------------------------- 4. 소요 표본
    # 관측된 효과크기(B비율)가 참값이라고 가정할 때 α=0.05·power=0.80으로
    # 0.5와 구분하려면 몇 건이 더 필요한가. 클러스터 때문에 유효표본이 줄어드는
    # 몫은 부트스트랩 CI 폭과 단순이항 CI 폭의 비(design effect)로 보정한다.
    Z_A, Z_B = 1.959964, 0.841621
    p_hat = b_all / n_all
    half_boot = (hi - lo) / 2
    half_simple = Z_A * math.sqrt(p_hat * (1 - p_hat) / n_all)
    deff = (half_boot / half_simple) ** 2
    n_simple = math.ceil(
        (Z_A * 0.5 + Z_B * math.sqrt(p_hat * (1 - p_hat))) ** 2 / (p_hat - 0.5) ** 2)
    n_clustered = math.ceil(n_simple * deff)

    # ---------------------------------------------------------------- 5. 상한
    # 그런데 그만큼 검수할 프레임이 **있는가**. Tier 1 규약은 run당 1프레임이고
    # (같은 run 안은 거의 중복이라 독립 표본으로 못 센다), 육안 판별이 되려면
    # different_person=1 · min_box_frac>=0.015 를 만족해야 한다.
    MIN_BOX_FRAC = 0.015
    _runs_all = defaultdict(list)
    for r in pop_frames:
        _runs_all[(r["clip_id"], run_start[(r["clip_id"], int(r["frame"]))])].append(r)
    runs_total = len(_runs_all)
    runs_reviewable = sum(
        any(r["different_person"] == "1" and float(r["min_box_frac"]) >= MIN_BOX_FRAC
            for r in v)
        for v in _runs_all.values())
    ceiling_reviewed = runs_reviewable + len(TIER0_CASE)
    ceiling_decided = math.floor(ceiling_reviewed * n_all / len(rows))

    result = {
        "n_reviewed": len(rows),
        "n_decided": n_all,
        "a_wins": a_all, "b_wins": b_all,
        "b_share": round(b_all / n_all, 4),
        "binomial_p_two_sided_frames": round(binom_two_sided(b_all, n_all), 4),
        "clip_level": {"B": cb, "A": ca, "tie": clip_verdicts["tie"],
                       "binomial_p_two_sided": round(clip_sign_p, 4)},
        "cluster_bootstrap_b_share_ci95": [round(lo, 4), round(hi, 4)],
        "cluster_bootstrap_iters": N_BOOT, "seed": SEED,
        "within_clip_unanimity": {
            "decided_clips": len(decided_clips),
            "unanimous_clips": len(unanimous),
            "clips_with_2plus_decided": len(multi),
            "unanimous_among_those": len(multi_unanimous),
        },
        "neutral_stratum": next(r for r in strat_rows
                                if r["subset"].startswith("비대칭항")),
        "power": {
            "assumed_b_share": round(p_hat, 4), "alpha": 0.05, "power": 0.80,
            "design_effect_from_cluster_bootstrap": round(deff, 3),
            "n_decided_needed_simple": n_simple,
            "n_decided_needed_clustered": n_clustered,
            "n_decided_now": n_all,
            "additional_decided_needed": max(0, n_clustered - n_all),
        },
        "ceiling_on_this_dataset": {
            "clips_with_disagreement": len({r["clip_id"] for r in pop_frames}),
            "disagreement_frames": len(pop_frames),
            "runs_total": runs_total,
            "runs_reviewable": runs_reviewable,
            "max_reviewable_frames": ceiling_reviewed,
            "max_decided_frames": ceiling_decided,
            "already_reviewed": len(rows),
            "sufficient": ceiling_decided >= n_clustered,
        },
    }
    (B4 / "clean_review_ab_test.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    # ---------------------------------------------------------------- 출력
    print("== 1. 전체·층별 ==")
    show(main_rows)
    print("\n== 2. 선정 편향: info_score 비대칭항으로 층화 ==")
    show(strat_rows)
    print("\n  공변량 분포 (모집단 vs 표본)")
    for r in cov_rows:
        print(f"    {r['covariate']:<15} 모집단(프레임) {r['population_frames']}  "
              f"모집단(run) {r['population_runs']}  표본 {r['reviewed_sample']}  "
              f"판정표본 {r['decided_sample']}   [info_score 가중치 {r['info_score_weight']}]")

    print("\n== 3. 클립 클러스터 ==")
    for c in clip_rows:
        print(f"  {c['clip_id']:<14} 검수 {c['n_reviewed']}  A {c['a_wins']} : B {c['b_wins']}"
              f"  판정제외 {c['excluded'] + c['neither']}  → {c['clip_verdict']}")
    print(f"  클립 단위 부호검정: B {cb} : A {ca} (동률 {clip_verdicts['tie']})  p={clip_sign_p:.4f}")
    print(f"  승패가 클립 안에서 몰리는 정도: 판정된 {len(decided_clips)}클립 중 "
          f"{len(unanimous)}클립이 만장일치, 2건 이상 판정된 {len(multi)}클립 중 "
          f"{len(multi_unanimous)}클립이 만장일치")
    print(f"  클러스터 부트스트랩 B비율 95% CI: [{lo:.3f}, {hi:.3f}]  "
          f"(점추정 {b_all / n_all:.3f}, 클립 {len(clips)}개 복원추출 {N_BOOT}회)")
    print(f"\n  → 0.5가 CI 안에 {'있다' if lo <= 0.5 <= hi else '없다'}")

    print("\n== 4. 지금 효과가 참값이라면 몇 건이 필요한가 (α=0.05, power=0.80) ==")
    print(f"  가정 B비율 {p_hat:.3f}   design effect {deff:.2f} (클러스터 부트스트랩 / 단순이항)")
    print(f"  판정 가능 표본 {n_simple}건(클러스터 무시) → {n_clustered}건(보정)  "
          f"현재 {n_all}건, 추가 {max(0, n_clustered - n_all)}건 필요")
    print(f"  판정 제외율 {1 - n_all / len(rows):.0%}를 감안하면 검수 이미지는 "
          f"약 {math.ceil(n_clustered / (n_all / len(rows)))}장")

    print("\n== 5. 그만큼 검수할 프레임이 이 데이터셋에 있는가 ==")
    print(f"  불일치 {len(pop_frames)}프레임 / run {runs_total}개 / "
          f"육안 판별 가능한 run {runs_reviewable}개 (클립 {len({r['clip_id'] for r in pop_frames})}개)")
    print(f"  run당 1프레임 규약에서 검수 가능한 최대 {ceiling_reviewed}장 → 판정 가능 최대 약 {ceiling_decided}건")
    print(f"  필요 {n_clustered}건 vs 상한 {ceiling_decided}건 → "
          f"{'충분' if ceiling_decided >= n_clustered else '부족 (이 데이터셋으로는 결론 불가)'}")
    print(f"  이미 {len(rows)}장을 봤으므로 남은 여유는 {ceiling_reviewed - len(rows)}장뿐이다.")


if __name__ == "__main__":
    main()
