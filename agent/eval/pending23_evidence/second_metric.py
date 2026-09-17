#!/usr/bin/env python3
"""밴드 지표를 고정하고 **두 번째 지표만 흔든다** (미결 23번).

    uv run python eval/pending23_evidence/second_metric.py

사전 등록: `PREREGISTRATION_second_metric.md`. 🔴 **조사 회차다** —
`src/`·`rubrics/` 를 고치지 않고 **import 만** 한다.

## 무엇을 가르려는가

가-3 뒤 남은 방향 오독 7건 중 4건이 `follow_through` 하나에 몰렸고, 형태가
같다 — 굴곡이 「짧음」 조각인데 *"지속 시간이 길어져 슈팅처럼 과도하게
뻗었다"*.

그런데 평가 스크립트가 비밴드 지표를 **상수 10.0** 으로 채워 왔다. 실측은
중앙 **4**(113건, 사분위 2~11)이고 프롬프트 앵커는 잘함 **4**·아쉬움 **1**
프레임이다. **10.0 은 앵커 어느 것보다 크다.** 그래서 모든 문장이 등급과
무관하게 「길다」를 보고 있었다.

**제품이 그러는 것인지, 계기가 그러게 만든 것인지**를 가른다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.judge import Judge, select_metrics  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

#: 실측 `follow_through_duration_frames` 의 최소 · 중앙 · 상위 사분위
#: (`eval/phaseA/phaseA_features.json` 113건). 🔴 결과를 보고 안 바꾼다.
DURATIONS = (1.0, 4.0, 11.0)

#: 밴드 안에서 값을 고를 위치 — `football_evidence.py` 와 같다.
FRACTIONS = (0.35, 0.65)

SECOND = "follow_through_duration_frames"


def value_in_band(criterion, grade: int, frac: float, seg: int) -> float:
    lo, hi = criterion.bands[grade][seg]
    if lo is None:
        return round(float(hi) * frac, 1)
    if hi is None:
        return round(float(lo) + 2.0 + 8.0 * frac, 1)
    return round(float(lo) + (float(hi) - float(lo)) * frac, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence_second_metric.json")
    args = ap.parse_args()

    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    judge = Judge()
    print(f"백엔드: {judge.backend} · 모델: {judge.model_id}")
    judge.load()

    clips: dict[str, dict] = {}
    try:
        for key, rubric in sorted(rubrics.items()):
            criterion = next(
                (c for c in rubric.criteria if SECOND in c.measured_by), None
            )
            if criterion is None:
                continue
            items = []
            for grade in (2, 1, 0):
                for seg in range(len(criterion.bands[grade])):
                    for frac in FRACTIONS:
                        band_value = value_in_band(criterion, grade, frac, seg)
                        for duration in DURATIONS:
                            features = {
                                criterion.band_metric: band_value,
                                SECOND: duration,
                            }
                            got = criterion.grade_for(features)
                            judged = judge.judge_criterion(
                                criterion, features, rubric.sport)
                            items.append({
                                "criterion_id": criterion.id,
                                "name": criterion.name,
                                "grade": grade,
                                # 🔴 **실제로 나온 등급**도 적는다 — 기준 Q3 가
                                #    「두 번째 지표가 등급을 움직이는가」다.
                                "graded_as": got,
                                "segment": seg,
                                "band_value": band_value,
                                "duration": duration,
                                "evidence": judged.get("evidence", ""),
                                "metric_ref": judged.get("metric_ref", ""),
                                "given_metrics": select_metrics(criterion, features),
                            })
            clips[key] = {"score": None, "grade": None, "items": items}
            print(f"  {key}/{criterion.id}: {len(items)}문장")
    finally:
        judge.unload()

    dest = HERE / args.out
    dest.write_text(json.dumps(
        {"tag": "second_metric", "backend": judge.backend,
         "model": judge.model_id, "durations": list(DURATIONS), "clips": clips},
        ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["items"]) for c in clips.values())
    print(f"\n{total}문장 → {dest.relative_to(ROOT)}")

    moved = sum(1 for c in clips.values() for i in c["items"]
                if i["grade"] != i["graded_as"])
    print(f"🔴 Q3 — 두 번째 지표가 등급을 움직인 건수: {moved} (0 이어야 한다)")


if __name__ == "__main__":
    main()
