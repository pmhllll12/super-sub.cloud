#!/usr/bin/env python3
"""축구 루브릭에서 지어낸 0.0 이 무엇을 했는지 — 실측값 위의 반사실 비교.

    uv run python eval/pending21_hip_rotation/football_path.py

**왜 이 형태인가.** B-6 Track 2 는 축구를 19편 × 5 selector = 95행 채점하는데,
그 19편은 다리 유효 비율이 0.93 이상이라 **문제의 조건(준비 구간에 다리 2프레임
미만)이 한 번도 발생하지 않았다.** 그래서 재실행만으로는 축구 경로에서 이 결함이
무엇을 했는지 보이지 않는다.

그래서 **실측 features 위에서 세 경우를 돌린다.** 포즈를 다시 뽑지 않는다 —
B-6 Track 2 CSV 가 지표 실측값을 그대로 담고 있고, 루브릭과 채점 코드는
production 을 import 한다.

    (가) 실측 그대로          — 다리가 보였을 때 실제로 나온 값
    (나) 0.0 을 지어냄        — 다리를 못 봤을 때의 **옛 동작**
    (다) 키 없음              — 다리를 못 봤을 때의 **새 동작**

🔴 **이것은 빈도가 아니라 결과의 크기를 보이는 것이다.** 이 19편에서 그 조건이
얼마나 자주 나는지는 여기서 알 수 없다(0건이었다). 나면 무슨 일이 벌어지는지를
잰다.

조사 스크립트라 `src/` 를 고치지 않는다 — import 만 한다.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import aggregate, load_rubric  # noqa: E402

CSV = ROOT / "eval" / "phaseA" / "eval_b6" / "selector_downstream_rubric_clips.csv"
RUBRIC = ROOT / "rubrics" / "football_instep_shot.yaml"

METRICS = (
    "plant_knee_angle_at_impact", "swing_knee_angle_at_impact",
    "trunk_forward_lean_deg_at_impact", "hip_rotation_range_deg",
    "swing_hip_flexion_after_impact_deg", "follow_through_duration_frames",
    "swing_elbow_angle_at_impact", "support_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg", "hip_shoulder_separation_deg",
)


def score(rubric, feats: dict) -> tuple[float, str, str]:
    crits = rubric.applicable_criteria(feats)
    judgments = {
        c.id: {"grade": c.grade_for(feats), "evidence": "", "metric_ref": ""}
        for c in crits
    }
    res = aggregate(judgments, rubric, [c.id for c in crits])
    hit = [b for b in res["breakdown"] if b["criterion_id"] == "hip_rotation"]
    tag = f"{hit[0]['grade']}등급/{hit[0]['title']}" if hit else "제외"
    return res["score"], res["grade"], tag


def main() -> None:
    rubric = load_rubric(RUBRIC)
    with open(CSV, encoding="utf-8") as fh:
        rows = [
            r for r in csv.DictReader(fh)
            if "football" in r["rubric"] and r["features_ok"] == "1"
            and r["hip_rotation_range_deg"].strip()
        ]

    print(f"루브릭: {RUBRIC.name} (status={rubric.status})")
    print(f"{'클립':24s}{'hip':>7s} | {'(가) 실측':>24s} | {'(나) 0.0 지어냄':>24s} | {'(다) 키 없음':>20s}")
    print("-" * 106)

    seen: set[str] = set()
    drops = renorm_gain = letter_drop = 0
    for r in rows:
        if r["clip_id"] in seen:
            continue
        seen.add(r["clip_id"])
        base = {m: float(r[m]) for m in METRICS if r[m].strip()}
        base["impact_frame"] = int(float(r["impact_frame"]))

        a = score(rubric, dict(base))
        b = score(rubric, {**base, "hip_rotation_range_deg": 0.0})
        c = score(rubric, {k: v for k, v in base.items() if k != "hip_rotation_range_deg"})

        if b[0] < a[0]:
            drops += 1
        if c[0] > b[0]:
            renorm_gain += 1
        if b[1] != a[1]:
            letter_drop += 1

        fmt = lambda t: f"{t[0]:5.1f}점 {t[1]:>2s} {t[2]}"  # noqa: E731
        print(f"{r['clip_id'][:24]:24s}{base['hip_rotation_range_deg']:7.1f} | "
              f"{fmt(a):>24s} | {fmt(b):>24s} | {fmt(c):>20s}")

    n = len(seen)
    print("-" * 106)
    print(f"클립 {n}편 중")
    print(f"  0.0 을 지어내면 점수가 떨어진 클립 : {drops}/{n}")
    print(f"  그중 **등급 문자까지** 떨어진 클립 : {letter_drop}/{n}")
    print(f"  키를 빼면 (나)보다 점수가 오른 클립: {renorm_gain}/{n}  ← 가중치 재정규화가 도는 증거")
    print("\n🔴 (다)는 (가)와 같지 않다 — 같아야 하는 것도 아니다.")
    print("   항목을 빼는 것은 재는 것과 다르다. 요점은 **안 잰 것으로 감점하지 않는다**는 것이다.")


if __name__ == "__main__":
    main()
