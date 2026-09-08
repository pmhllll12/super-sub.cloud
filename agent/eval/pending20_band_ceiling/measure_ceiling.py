#!/usr/bin/env python3
"""0등급이 **어느 쪽 끝에서** 왔는지 센다 — 위(상한 초과)인가 아래(진짜 못함)인가.

    uv run python eval/pending20_band_ceiling/measure_ceiling.py

미결 20번은 「상한 초과가 0등급으로 나간다」이고, 그 수치가 **야구 타격
46클립에서만** 나와 있었다(분리각 8/15, 팔로스루 12/20). 투구·축구·농구는
"같은 구조다"라고만 적혀 있고 재지 않았다. 여기서 **6개 루브릭 전부**를 잰다.

입력은 이미 있는 실측이다 — 포즈를 다시 뽑지 않는다.

  · 야구 타격 : `eval/jhmdb_batting/features_swing_baseball.json` (JHMDB 46)
  · 나머지 5개: `eval/phaseA/eval_b6/selector_downstream_rubric_clips.csv`
                (B-6 Track 2, 22편 × 5 selector — 클립당 baseline 행만 쓴다)

**판정 규칙은 production 을 쓴다.** `Criterion.grade_for` 로 등급을 받고,
상한은 `bands` 의 최상위 등급 구간에서 읽는다 — 루브릭 YAML 을 다시 해석하지
않는다(해석이 갈리면 그 자체가 새 결함이다).

🔴 **이것은 처방이 아니라 크기 재기다.** 어느 처방(가·나·다)이 옳은지는
임계값 검수(미결 2번)에 달려 있고 여기서 고르지 않는다.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import Criterion, load_rubric  # noqa: E402

TRACK2 = ROOT / "eval" / "phaseA" / "eval_b6" / "selector_downstream_rubric_clips.csv"
BATTING = ROOT / "eval" / "jhmdb_batting" / "features_swing_baseball.json"

RUBRIC_OF = {
    "football/instep_shot": "football_instep_shot.yaml",
    "baseball/pitching": "baseball_pitching.yaml",
    "basketball/jump_shot": "basketball_jump_shot.yaml",
    "basketball/layup": "basketball_layup.yaml",
}

METRIC_COLS = (
    "plant_knee_angle_at_impact", "swing_knee_angle_at_impact",
    "trunk_forward_lean_deg_at_impact", "hip_rotation_range_deg",
    "swing_hip_flexion_after_impact_deg", "follow_through_duration_frames",
    "swing_elbow_angle_at_impact", "support_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg", "hip_shoulder_separation_deg",
)


def top_ceiling(c: Criterion) -> float | None:
    """최상위 등급 구간의 **닫힌 위끝**. 위가 열려 있으면 None."""
    if not c.bands:
        return None
    intervals = c.bands.get(max(c.bands), ())
    highs = [hi for _lo, hi in intervals if hi is not None]
    return max(highs) if highs else None


def classify(c: Criterion, feats: dict) -> str | None:
    """0등급이면 'above'(상한 초과) 또는 'below'(진짜 아래), 아니면 None."""
    if not c.is_applicable(feats) or c.band_metric not in feats:
        return None
    if c.grade_for(feats) != 0:
        return None
    ceil = top_ceiling(c)
    if ceil is None:
        return "below"
    return "above" if float(feats[c.band_metric]) > ceil else "below"


def tally(rubric, samples) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for c in rubric.criteria:
        above = below = 0
        for feats in samples:
            k = classify(c, feats)
            if k == "above":
                above += 1
            elif k == "below":
                below += 1
        if above or below:
            out[c.id] = (above, below)
    return out


def main() -> None:
    jobs: list[tuple[str, object, list[dict]]] = []

    data = json.loads(BATTING.read_text(encoding="utf-8"))
    batting = [x["features"] for x in data["records"] if "features" in x]
    jobs.append(("baseball/batting (JHMDB 46)",
                 load_rubric(ROOT / "rubrics" / "baseball_batting.yaml"), batting))

    with open(TRACK2, encoding="utf-8") as fh:
        t2_all = [r for r in csv.DictReader(fh) if r["comparison_selector"] == "baseline"]
    t2 = [r for r in t2_all if r["features_ok"] == "1"]
    for key, name in RUBRIC_OF.items():
        samples = []
        for r in (x for x in t2 if x["rubric"] == key):
            f = {m: float(r[m]) for m in METRIC_COLS if r[m].strip()}
            f["impact_frame"] = int(float(r["impact_frame"]))
            samples.append(f)
        if samples:
            jobs.append((f"{key} (B-6 Track2 {len(samples)}편)",
                         load_rubric(ROOT / "rubrics" / name), samples))
        else:
            # 표본이 0이면 그 이유를 말한다 — 조용히 빠지면 "문제 없음"으로 읽힌다.
            n_all = sum(1 for x in t2_all if x["rubric"] == key)
            print(f"⚠ {key}: 측정 성공 표본 0편 "
                  f"(Track2 에 {n_all}행 있으나 전부 features_ok=0) — 재지 못했다")

    grand_above = grand_zero = 0
    for label, rubric, samples in jobs:
        res = tally(rubric, samples)
        print(f"\n=== {label} · status={rubric.status} ===")
        if not res:
            print("  0등급 없음")
            continue
        print(f"  {'항목':32s} {'0등급':>5s} {'상한초과':>7s} {'아래':>5s}")
        for cid, (above, below) in res.items():
            z = above + below
            grand_above += above
            grand_zero += z
            mark = "  🔴" if above else ""
            print(f"  {cid:32s} {z:5d} {above:7d} {below:5d}{mark}")

    # --- 구조 점검 — 표본이 없어도 **샐 수 있는 자리**는 셀 수 있다 -----------
    #
    # 항목이 "같은 구조다"라고만 적혀 있던 것을 실제로 확인한다. 위가 닫힌
    # 최상위 구간을 가진 항목은 **초과값이 갈 곳이 0등급뿐이다**.
    print(f"\n{'='*62}\n구조 점검 — 상한이 닫혀 있어 **샐 수 있는** 항목 (표본 무관)\n{'='*62}")
    all_rubrics = ["baseball_batting.yaml", "baseball_pitching.yaml",
                   "basketball_jump_shot.yaml", "basketball_layup.yaml",
                   "football_inside_pass.yaml", "football_instep_shot.yaml"]
    for name in all_rubrics:
        rb = load_rubric(ROOT / "rubrics" / name)
        closed = [c.id for c in rb.criteria if top_ceiling(c) is not None]
        opened = [c.id for c in rb.criteria if c.bands and top_ceiling(c) is None]
        print(f"  {name[:-5]:24s} status={rb.status:6s} "
              f"닫힘 {len(closed)}/{len(rb.criteria)}" + (f" · 열림 {opened}" if opened else ""))

    pct = 100.0 * grand_above / grand_zero if grand_zero else 0.0
    print(f"\n{'='*62}")
    print(f"전체 0등급 {grand_zero}건 중 **상한 초과 {grand_above}건 ({pct:.0f}%)**")
    print("상한 초과는 「쟀는데 못했다」가 아니라 「구간 밖이다」인데 같은 0점이 된다.")
    print("🔴 처방(가·나·다)은 여기서 고르지 않는다 — 임계값 검수(미결 2번)에 달려 있다.")


if __name__ == "__main__":
    main()
