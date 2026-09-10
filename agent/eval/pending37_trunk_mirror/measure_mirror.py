#!/usr/bin/env python3
"""상체 기울기의 **촬영 방향 의존** — 크기를 잰다 (미결 `ho` 37번).

    uv run python eval/pending37_trunk_mirror/measure_mirror.py    # GPU 불필요

기전은 코드가 이미 답했다:

    trunk_lean = degrees(arctan2(trunk[0], -trunk[1]))    # trunk[0] = 이미지 x

`normalize()` 는 평행이동(골반중심→원점)과 스케일(어깨너비)만 한다 — **방향을
정규화하지 않는다.** 그래서 좌우를 반전하면 `trunk[0]` 만 부호가 바뀌어 각도가
**정확히 `-θ`** 가 된다. 이 지표는 「앞으로 기울었나」가 아니라 **「이미지
오른쪽으로 기울었나」**를 잰다.

**증명할 것이 아니라 크기를 잴 것이다.** 여섯 루브릭 중 야구 타격만 밴드가
0 에 대칭이고(rationale 에 이유가 적혀 있다) **나머지 다섯은 비대칭**이다.

방법은 **실측 위 반사실**이다(미결 21번이 축구에 쓴 방식) — 포즈를 다시 뽑지
않고 `trunk_forward_lean` 만 부호를 뒤집어 다시 채점한다. 🔴 반사실이 성립하는
근거는 사전 등록의 지표별 표에 있다: **반전에 민감한 지표는 이것 하나뿐이다.**

규격은 `PREREGISTRATION.md`(커밋 `adff28f`, 코드보다 먼저).

🔴 **`features.py`·`rubrics/`·앞 회차 스크립트를 고치지 않는다.** import 만 한다.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import Rubric, aggregate, load_rubric  # noqa: E402

TRACK2 = ROOT / "eval" / "phaseA" / "eval_b6" / "selector_downstream_rubric_clips.csv"
BATTING = ROOT / "eval" / "jhmdb_batting" / "features_swing_baseball.json"

METRIC = "trunk_forward_lean_deg_at_impact"

# 사전 등록 「표본」 — 있는 실측만 쓴다. 새로 만들지 않는다.
RUBRIC_FILE = {
    "football/instep_shot": "football_instep_shot.yaml",
    "baseball/pitching": "baseball_pitching.yaml",
    "basketball/jump_shot": "basketball_jump_shot.yaml",
    "basketball/layup": "basketball_layup.yaml",
    "baseball/batting": "baseball_batting.yaml",
}
# 🔴 표본이 아예 없는 것. 밴드가 비대칭이라 같은 결함이 있을 것이 거의
#    확실하지만 **재지 않았으므로 수를 적지 않는다.**
NO_SAMPLE = ("football/inside_pass",)

# 유효 분모가 이 아래면 **비율을 내지 않고 분모만 보고한다** (사전 등록).
SMALL_N = 10

# 부호가 이 안이면 「0 근처」로 센다 — 0 을 경계로 쓰는 밴드는 측정 잡음만으로
# 등급이 갈린다. 🔴 데이터를 보기 전에 박은 값이다.
NEAR_ZERO_DEG = 5.0

NUMERIC = (
    "impact_frame", "swing_knee_angle_at_impact", "plant_knee_angle_at_impact",
    METRIC, "hip_rotation_range_deg", "swing_hip_flexion_after_impact_deg",
    "follow_through_duration_frames", "swing_elbow_angle_at_impact",
    "support_elbow_angle_at_impact", "swing_shoulder_flexion_after_impact_deg",
    "hip_shoulder_separation_deg",
)


def score_of(rubric: Rubric, feats: dict):
    """production 경로로 (총점, 등급). 판정 가능한 항목이 없으면 None.

    앞 회차(`pending20_band_floor`)와 **같은 규칙**이다 — 등급 판정과 합산만
    떼어 쓴다. 근거 문장은 모델이 쓰지만 등급은 결정론적 코드가 정한다.
    """
    try:
        applicable = rubric.applicable_criteria(feats)
    except Exception:
        return None
    judgments = {}
    for c in applicable:
        try:
            judgments[c.id] = {"grade": c.grade_for(feats),
                               "evidence": "", "metric_ref": ""}
        except Exception:
            return None
    if not judgments:
        return None
    out = aggregate(judgments, rubric, features=feats)
    return out["score"], out["grade"]


def trunk_grade(rubric: Rubric, feats: dict):
    """이 지표로 등급을 정하는 항목의 등급. 없으면 None."""
    for c in rubric.criteria:
        if c.band_metric != METRIC or not c.is_applicable(feats):
            continue
        try:
            return c.id, c.grade_for(feats)
        except Exception:
            return c.id, None
    return None, None


def mirrored(feats: dict) -> dict:
    """🔴 이 회차의 유일한 변경 — `trunk_lean` 만 부호를 뒤집는다.

    나머지는 **한 비트도** 건드리지 않는다. 반전에 다른 지표가 안 변한다는
    것은 사전 등록에서 지표별로 확인했다.
    """
    out = dict(feats)
    out[METRIC] = -feats[METRIC]
    return out


def load_track2():
    """🔴 **클립 단위**로 읽는다 — 행 단위가 아니다.

    Track 2 는 `클립 × comparison_selector` 라 한 클립이 5행으로 늘어난다.
    행을 세면 **같은 측정을 다섯 번 센다** — 실제로 점프슛 「5건」은 클립
    **하나**(`bball_shot.mp4`)였다. 사전 등록이 표본을 「110행 / 5건씩」으로
    적은 것이 그 착오였고, `RESULTS.md` 「정정」 절에 남겼다.

    `comparison_selector == "baseline"` 이 **클립당 정확히 한 행**이고
    production 경로다(확인: 중복 없음).
    """
    rows = []
    for r in csv.DictReader(TRACK2.open(encoding="utf-8")):
        if r.get("comparison_selector", "").strip() != "baseline":
            continue
        if r.get("features_ok", "").strip().lower() not in ("true", "1", "yes"):
            continue
        feats = {}
        for k in NUMERIC:
            v = (r.get(k) or "").strip()
            if v in ("", "None", "nan"):
                continue
            feats[k] = float(v)
        if METRIC not in feats:
            continue
        rows.append((r["rubric"], r["clip_id"], feats))
    return rows


def load_batting():
    d = json.loads(BATTING.read_text(encoding="utf-8"))
    out = []
    for rec in d["records"]:
        feats = rec.get("features") or {}
        if METRIC not in feats:
            continue
        out.append(("baseball/batting", rec["clip"], dict(feats)))
    return out


def main() -> None:
    samples = load_track2() + load_batting()
    rubrics = {k: load_rubric(ROOT / "rubrics" / v) for k, v in RUBRIC_FILE.items()}

    by_rubric: dict[str, list] = {}
    for key, clip, feats in samples:
        if key in rubrics:
            by_rubric.setdefault(key, []).append((clip, feats))

    print("═" * 96)
    print("표본 — 🔴 **클립 단위**다 (사전 등록의 「행」을 정정했다. RESULTS 「정정」 절)")
    print("═" * 96)
    for key in RUBRIC_FILE:
        n = len(by_rubric.get(key, []))
        if n == 0:
            print(f"  {key:24s}    0클립  🔴 실측이 없다 — 아래에서 사유를 적는다")
            continue
        small = "  ⚠️ 분모가 한 자릿수 — 비율을 내지 않는다" if n < SMALL_N else ""
        print(f"  {key:24s} {n:4d}클립{small}")
    for key in NO_SAMPLE:
        print(f"  {key:24s}    — 🔴 **표본이 없다.** 밴드는 비대칭이지만 "
              "재지 않았으므로 수를 적지 않는다")

    # --- 자기 검사 (기준 B·C) ------------------------------------------
    sign_exact = other_same = True
    for _key, _clip, feats in samples:
        m = mirrored(feats)
        if m[METRIC] != -feats[METRIC]:
            sign_exact = False
        if {k: v for k, v in m.items() if k != METRIC} != \
           {k: v for k, v in feats.items() if k != METRIC}:
            other_same = False

    print("\n" + "═" * 96)
    print("결과 — 🔴 루브릭별로 적는다. 합계로 말하지 않는다 (인스텝이 18/66 클립이다)")
    print("═" * 96)
    print(f"  {'rubric':24s} │ {'n':>4s} │ {'항목등급 변동':>12s} │ "
          f"{'최종등급 변동':>12s} │ {'총점 변동(평균/최악)':>20s}")

    verdicts = {}
    for key in RUBRIC_FILE:
        rows = by_rubric.get(key, [])
        if not rows:
            continue
        rubric = rubrics[key]
        crit_changed = grade_changed = 0
        deltas = []
        n_scored = 0
        for _clip, feats in rows:
            _cid, g0 = trunk_grade(rubric, feats)
            _cid, g1 = trunk_grade(rubric, mirrored(feats))
            if g0 is not None and g1 is not None and g0 != g1:
                crit_changed += 1
            a = score_of(rubric, feats)
            b = score_of(rubric, mirrored(feats))
            if a and b:
                n_scored += 1
                deltas.append(abs(a[0] - b[0]))
                if a[1] != b[1]:
                    grade_changed += 1
        avg = sum(deltas) / len(deltas) if deltas else 0.0
        worst = max(deltas) if deltas else 0
        small = len(rows) < SMALL_N
        fmt = (lambda c, n: f"{c}/{n}") if small else \
              (lambda c, n: f"{c}/{n} ({c / n:.0%})")
        verdicts[key] = (len(rows), crit_changed, grade_changed, avg, worst)
        print(f"  {key:24s} │ {len(rows):4d} │ "
              f"{fmt(crit_changed, len(rows)):>12s} │ "
              f"{fmt(grade_changed, n_scored or 1):>12s} │ "
              f"{avg:9.1f} / {worst:<8.0f}")

    # --- 🔴 핵심: 반전 없이 본 원 실측의 부호 분포 ----------------------
    print("\n" + "═" * 96)
    print("🔴 반전 **없이** — 원 실측의 부호 분포. 이 회차의 핵심이다")
    print("═" * 96)
    print("  한쪽 부호만 나오면 「이론상 결함이지만 이 데이터에선 안 난다」이고,")
    print("  **양쪽이 다 나오면 이미 나고 있다.**\n")
    print(f"  {'rubric':24s} │ {'음수':>6s} {'양수':>6s} │ "
          f"{'|θ| < ' + str(NEAR_ZERO_DEG) + '도':>12s} │ 범위")
    both_sides = []
    for key in RUBRIC_FILE:
        rows = by_rubric.get(key, [])
        if not rows:
            continue
        vals = [f[METRIC] for _c, f in rows]
        neg = sum(1 for v in vals if v < 0)
        pos = sum(1 for v in vals if v > 0)
        near = sum(1 for v in vals if abs(v) < NEAR_ZERO_DEG)
        if neg and pos:
            both_sides.append(key)
        print(f"  {key:24s} │ {neg:6d} {pos:6d} │ {near:12d} │ "
              f"{min(vals):7.1f} ~ {max(vals):.1f}")

    print("\n" + "═" * 96)
    print("사전 등록 기준 (커밋 `adff28f` — 결과를 보고 바꾸지 않았다)")
    print("═" * 96)
    bat = verdicts.get("baseball/batting")
    a_ok = bat is not None and bat[1] == 0 and bat[2] == 0
    print(f"  A 자기 검사 — 야구 타격(대칭 밴드) 변동 0건 …… "
          f"{'✅ 만족' if a_ok else '🔴 불만족'}"
          + (f"   (항목 {bat[1]}건 · 최종 {bat[2]}건)" if bat else "   (표본 없음)"))
    print(f"  B 반사실이 정확한 음수인가 ………………………… "
          f"{'✅ 만족' if sign_exact else '🔴 불만족'}")
    print(f"  C 나머지 지표가 한 비트도 안 변하는가 ………… "
          f"{'✅ 만족' if other_same else '🔴 불만족'}")
    print("  D `features.py`·`rubrics/` 미수정 ………………… ✅ import 만 했다")

    print("\n" + "═" * 96)
    if both_sides:
        print("판정: 🔴 **이미 나고 있다.** 원 실측에서 **양쪽 부호가 다 나오는** "
              "루브릭: " + ", ".join(both_sides))
        print("   같은 자세라도 피사체가 향한 쪽에 따라 다른 등급을 받는다는 뜻이다.")
    else:
        print("판정: ⚠️ 원 실측에서는 **한쪽 부호만** 나왔다 — 이론상 결함이지만")
        print("   이 표본에서는 드러나지 않는다. 표본의 촬영 방향 쏠림일 수 있다.")
    print("🔴 「그래서 지금 점수가 틀렸다」로는 못 간다 — **정답이 없다.** 말할 수")
    print("   있는 것은 「같은 자세가 촬영 방향에 따라 다른 등급을 받는다」까지다.")
    print("🔴 밴드를 고치지 않았고 `features.py` 에 방향 정규화를 넣지 않았다 —")
    print("   전자는 임계값 이동(34번·2번), 후자는 B-6 전 구간 재실행이다.")


if __name__ == "__main__":
    main()
