#!/usr/bin/env python3
"""미결 20번 **아래쪽 끝** — 관절각의 하한이 기하 한계라서 새는 양을 잰다.

    uv run python eval/pending20_band_floor/measure_floor.py     # GPU 불필요

상한은 2026.09.08에 전 루브릭으로 쟀고(`eval/pending20_band_ceiling/`) 그
회차가 「하한 쪽은 이번에 재지 않았다」고 적어 두었다. 아래쪽 근거는 아직
실클립 4건뿐이다(`support_elbow` 5.4도 · `plant_knee` 24.3도 ·
`swing_knee` 29.0도). 그 크기를 여기서 잰다.

🔴 **하한값을 고르지 않는다.** 「팔꿈치는 몇 도 아래가 불가능한가」는 임계값
검수(미결 2번)의 성격이고, 분포를 보고 그으면 이미 기각된 경로다(`ho` 34번).
대신 **후보 하한 L 에 대한 민감도 곡선**을 낸다 — 검수자가 L 을 고를 때 필요한
숫자를 미리 준비해 두는 것이 목적이다.

설계·격자·해석 규칙은 데이터를 보기 전에 `PREREGISTRATION.md` 에 박았다
(커밋 `933a277`). 격자를 결과를 보고 늘리거나 줄이지 않는다.

입력은 이미 있는 실측이다 — 포즈를 다시 뽑지 않고 `src/` 도 고치지 않는다.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import Rubric, aggregate, load_rubric  # noqa: E402

TRACK2 = ROOT / "eval" / "phaseA" / "eval_b6" / "selector_downstream_rubric_clips.csv"
BATTING = ROOT / "eval" / "jhmdb_batting" / "features_swing_baseball.json"

# 사전 등록 「후보 하한 격자」 — 데이터를 보기 전에 박았다.
GRID = (5, 10, 15, 20, 25, 30, 35, 40)

# 사전 등록 「대상 지표」 — joint_angle(arccos) 이라 0이 **기하학적 최소**이고
# 사람 관절이 갈 수 없는 값인 것 넷. 나머지 둘(`*_after_impact_deg`)은 각도가
# 아니라 **증분**이고, hip_rotation_range 는 범위, hip_shoulder_separation 은
# 차이, trunk_lean 은 부호값이라 0이 정당하다 — 전부 제외한다.
JOINT_ANGLES = (
    "plant_knee_angle_at_impact",
    "swing_knee_angle_at_impact",
    "swing_elbow_angle_at_impact",
    "support_elbow_angle_at_impact",
)

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


def score_of(rubric: Rubric, feats: dict) -> tuple[int, str] | None:
    """production 경로로 총점·등급을 낸다. 판정 가능한 항목이 없으면 None.

    `judge.py` 가 하는 일 중 **등급 판정과 합산만** 떼어 쓴다 — 근거 문장은
    모델이 쓰지만 등급은 결정론적 코드가 정한다(`README.md` 첫 절).
    """
    try:
        applicable = rubric.applicable_criteria(feats)
    except Exception:
        return None
    judgments = {}
    for c in applicable:
        try:
            judgments[c.id] = {"grade": c.grade_for(feats), "evidence": "", "metric_ref": ""}
        except Exception:
            return None
    if not judgments:
        return None
    out = aggregate(judgments, rubric, features=feats)
    return out["score"], out["grade"]


def zero_graded(rubric: Rubric, feats: dict, metric: str) -> bool:
    """이 지표로 등급을 정하는 항목이 지금 **0등급**인가."""
    for c in rubric.criteria:
        if c.band_metric != metric or not c.is_applicable(feats):
            continue
        if metric not in feats:
            continue
        try:
            if c.grade_for(feats) == 0:
                return True
        except Exception:
            continue
    return False


def main() -> None:
    jobs: list[tuple[str, Rubric, list[dict]]] = []

    data = json.loads(BATTING.read_text(encoding="utf-8"))
    batting = [x["features"] for x in data["records"] if "features" in x]
    jobs.append(("baseball/batting (JHMDB 46)",
                 load_rubric(ROOT / "rubrics" / "baseball_batting.yaml"), batting))

    # 🔴 사전 등록 **뒤에** 더한 표본이다 — 이유를 남긴다.
    #
    # 사전 등록은 입력을 「상한 회차와 같은 것」으로 적었는데, 미결 20번이
    # 아래쪽 근거로 든 4건(`plant_knee` 24.3도 · `swing_knee` 29.0도)은
    # **JHMDB 46 에 없다.** 별도 표본(Kinetics 실클립)이다. 빼고 내면
    # 「무릎은 깨끗하다」로 잘못 보고하게 되므로 더한다.
    #
    # 격자·대상 지표·보고 항목은 그대로다 — 고른 것이 아니라 항목이 이미
    # 지목해 둔 표본이다.
    realclip = []
    for p in sorted((ROOT / "eval" / "jhmdb_batting" / "realclip").glob("*_result.json")):
        f = json.loads(p.read_text(encoding="utf-8")).get("features")
        if f:
            realclip.append(f)
    if realclip:
        jobs.append((f"baseball/batting 실클립 {len(realclip)}건 (항목의 원 근거)",
                     load_rubric(ROOT / "rubrics" / "baseball_batting.yaml"), realclip))

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
            # 사전 등록: 조용히 빠지면 「문제 없음」으로 읽히므로 명시한다.
            n_all = sum(1 for x in t2_all if x["rubric"] == key)
            print(f"⚠ {key}: 측정 성공 표본 0편 "
                  f"(Track2 에 {n_all}행 있으나 전부 features_ok=0) — 이번에도 못 쟀다")

    # --- 0) 무엇이 실제로 관측됐나 — 최솟값부터 보인다 ----------------------
    print(f"\n{'='*72}\n0) 관절각 4개의 **실측 최솟값** (하한이 문제가 되는 자리)\n{'='*72}")
    print(f"  {'루브릭':34s} {'지표':34s} {'n':>4s} {'최소':>7s}")
    for label, _rb, samples in jobs:
        for m in JOINT_ANGLES:
            vals = [float(f[m]) for f in samples if m in f]
            if vals:
                print(f"  {label[:34]:34s} {m:34s} {len(vals):4d} {min(vals):7.1f}")

    # --- (a)(b) 민감도 곡선 --------------------------------------------------
    print(f"\n{'='*72}\n(a)(b) 후보 하한 L 별 — 걸리는 값 / 그중 지금 0등급\n{'='*72}")
    print(f"  {'L(도)':>6s} {'걸리는 값':>10s} {'그중 0등급':>11s}   지표별 내역")
    curve: dict[int, tuple[int, int]] = {}
    for L in GRID:
        hit = zero = 0
        detail: dict[str, int] = {}
        for _label, rb, samples in jobs:
            for f in samples:
                for m in JOINT_ANGLES:
                    if m in f and float(f[m]) < L:
                        hit += 1
                        detail[m] = detail.get(m, 0) + 1
                        if zero_graded(rb, f, m):
                            zero += 1
        curve[L] = (hit, zero)
        d = " · ".join(f"{k.replace('_angle_at_impact','')}={v}" for k, v in sorted(detail.items()))
        print(f"  {L:6d} {hit:10d} {zero:11d}   {d}")

    # --- (c) 반사실 — 그 값을 빼면 등급이 어떻게 되나 ------------------------
    #
    # 🔴 실측 features **사본** 위에서만 지운다. src/ 도 저장된 CSV 도 안 건드린다.
    # 미결 21번 `football_path.py` 와 같은 형태다.
    print(f"\n{'='*72}\n(c) 반사실 — L 미만을 **빼고** 다시 채점하면\n{'='*72}")
    # 🔴 등급 변화가 **어느 루브릭에서** 났는지 함께 낸다. 야구 타격은
    # `draft` 라 선수 화면에 안 나간다 — 같은 「등급 변화 4건」이라도
    # active 에서 났는지 draft 에서 났는지가 전혀 다른 사실이다.
    print(f"  {'L(도)':>6s} {'영향 클립':>9s} {'점수 변화':>10s} {'등급 문자 변화':>14s}   등급 변화의 출처")
    for L in GRID:
        touched = moved_score = moved_grade = 0
        by_rubric: dict[str, int] = {}
        for label, rb, samples in jobs:
            for f in samples:
                drop = [m for m in JOINT_ANGLES if m in f and float(f[m]) < L]
                if not drop:
                    continue
                before = score_of(rb, f)
                after = score_of(rb, {k: v for k, v in f.items() if k not in drop})
                if before is None or after is None:
                    continue
                touched += 1
                if before[0] != after[0]:
                    moved_score += 1
                if before[1] != after[1]:
                    moved_grade += 1
                    tag = f"{label.split(' (')[0]}[{rb.status}]"
                    by_rubric[tag] = by_rubric.get(tag, 0) + 1
        src = " · ".join(f"{k}={v}" for k, v in sorted(by_rubric.items())) or "—"
        print(f"  {L:6d} {touched:9d} {moved_score:10d} {moved_grade:14d}   {src}")

    print(f"\n{'='*72}")
    print("🔴 어느 L 이 옳은지는 여기서 말하지 않는다 — 임계값 검수(미결 2번)다.")
    print("🔴 표본에서 0건이라도 「결함이 없다」가 아니다 — 실클립 4건의 증거는 남는다.")
    print("🔴 농구 둘은 표본이 각 1편이다. 0이 「안 샌다」는 뜻이 아니다.")


if __name__ == "__main__":
    main()
