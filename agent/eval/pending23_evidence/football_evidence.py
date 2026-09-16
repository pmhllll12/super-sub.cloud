"""**축구 루브릭**으로 근거 문장을 만들어 같은 R1·R2·R3 로 판정한다 (미결 23번).

    uv run python eval/pending23_evidence/football_evidence.py
    uv run python eval/pending23_evidence/check_evidence.py evidence_football.json

## 🔴 왜 만들었나 — 야구 픽스처는 이제 제품이 아니다

23번의 기준선 19문장은 **야구 타격**이고, 그 루브릭은 2026.09.11 축구 단일 종목
전환에서 **지워졌다**(미결 39번). 그래서 지금까지는 잴 때마다 지운 루브릭을
`git show` 로 되살려야 했고, **재는 대상이 제품이 아니었다.**

이 스크립트는 같은 질문을 **살아 있는 루브릭**에 묻는다. 🔴 **판정 규칙은
그대로다** — `check_evidence.py`(사전 등록된 R1·R2·R3)를 고치지 않고 그것이
읽을 수 있는 모양으로 낸다.

## 야구 기준선과 **바로 비교하지 않는다**

문장 수도(19 대 아래) 루브릭도 다르다. 이쪽은 **앞으로의 기준선**이고,
야구 19문장은 **2026.09.07 까지의 기록**으로 남는다.

## 정답이 필요 없다

R1(「등급」 낱말)·R2(구간 표기)는 **표기**를 세므로 라벨이 필요 없다. 🔴 「감점을
칭찬으로 서술하는가」(역방향)는 여기서도 **안 센다** — 문자열로 가르려 하면 그
검사가 또 틀리고, 틀린 검사는 「검사했다」는 인상만 남긴다(23번 본문).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.judge import Judge, select_metrics  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

#: 밴드 안에서 값을 고를 위치. 등급마다 두 점씩 — 한 점이면 그 값 하나에만
#: 맞춰진 문장을 보게 된다.
FRACTIONS = (0.35, 0.65)


def value_in_band(criterion, grade: int, frac: float) -> float:
    lo, hi = criterion.bands[grade][0]
    if lo is None:
        return round(float(hi) * frac, 1)
    if hi is None:
        return round(float(lo) + 2.0 + 8.0 * frac, 1)
    return round(float(lo) + (float(hi) - float(lo)) * frac, 1)


def main() -> None:
    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    judge = Judge()
    print(f"백엔드: {judge.backend} · 모델: {judge.model_id}")
    judge.load()

    clips: dict[str, dict] = {}
    try:
        for key, rubric in sorted(rubrics.items()):
            items = []
            for criterion in rubric.criteria:
                for grade in (2, 1, 0):
                    for frac in FRACTIONS:
                        features = {criterion.band_metric:
                                    value_in_band(criterion, grade, frac)}
                        # 밴드 지표 말고 `measured_by` 에 있는 것도 채운다 —
                        # 프롬프트가 그것들도 보여주기 때문이다.
                        for code in criterion.measured_by:
                            features.setdefault(code, 10.0)
                        got = criterion.grade_for(features)
                        if got != grade:
                            continue  # 밴드가 갈라져 있으면 건너뛴다(정직하게)
                        judged = judge.judge_criterion(
                            criterion, features, rubric.sport)
                        items.append({
                            "criterion_id": criterion.id,
                            "name": criterion.name,
                            "grade": grade,
                            "stored_grade": grade,
                            "evidence": judged.get("evidence", ""),
                            "metric_ref": judged.get("metric_ref", ""),
                            "given_metrics": select_metrics(criterion, features),
                        })
            clips[key] = {"score": None, "grade": None, "items": items}
            print(f"  {key}: {len(items)}문장")
    finally:
        judge.unload()

    dest = HERE / "evidence_football.json"
    dest.write_text(json.dumps(
        {"tag": "football", "backend": judge.backend, "model": judge.model_id,
         "clips": clips}, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["items"]) for c in clips.values())
    print(f"\n{len(clips)}루브릭 {total}문장 → {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
