"""**어디서 오는 말인가** — 취지·옆 등급 앵커를 끄고 다시 만든다 (미결 23번 C).

    uv run python eval/pending23_evidence/source_trace.py --arm C1
    uv run python eval/pending23_evidence/source_trace.py --arm C2
    uv run python eval/pending23_evidence/source_trace.py --arm C3
    uv run python eval/pending23_evidence/source_trace.py --arm C0 --only hip_rotation

사전 등록: `PREREGISTRATION_source_trace.md`. 결과를 보고 이 스크립트를 고치지
않는다.

## 무엇을 끄는가

`inside_pass/hip_rotation` **85.8**(과회전)이 B 뒤에도 *"인사이드 면이 공에
충분히 닿지 않아"*(덜 열림 방향)라고 쓴다. 그 어구가 프롬프트의 **취지**에서
오는지 **옆 등급 앵커**에서 오는지 **모델 자신**인지 가른다.

| 팔 | 취지 | 옆 등급 앵커 |
|---|---|---|
| C0 | 있음 | 있음 |
| C1 | **없음** | 있음 |
| C2 | 있음 | **없음** |
| C3 | **없음** | **없음** |

🔴 **조사 회차라 `src/` 도 `rubrics/*.yaml` 도 안 고친다.** 루브릭은 데이터이고
`Criterion` 은 frozen dataclass이므로 `dataclasses.replace` 로 **사본**을 만들어
`judge_criterion` 에 넘긴다. 제품 프롬프트는 B 그대로다.

🔴 **계기는 `football_evidence.py` 를 import 한다** — `FRACTIONS`·`value_in_band`·
`filler` 를 베껴 쓰면 한쪽만 고쳐진다. 채우는 값도 **원본 항목**으로 구한다:
앵커를 지운 사본으로 구하면 팔마다 측정값이 달라져 대조가 깨진다.

🔴 **어느 팔도 제품에 올리지 않는다.** C2·C3 는 1회차에서 잘함 문장 8건 중
4건을 무너뜨린 그 방향이다. 처방은 결과를 보고 새 사전 등록으로 연다.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from football_evidence import FRACTIONS, filler, value_in_band  # noqa: E402
from supersub_agent.judge import Judge, select_metrics  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

#: 팔 이름 → (취지를 끄는가, 옆 등급 앵커를 끄는가)
ARMS = {
    "C0": (False, False),
    "C1": (True, False),
    "C2": (False, True),
    "C3": (True, True),
}


def ablated(criterion, grade: int, band_value: float | None,
            drop_rationale: bool, drop_other_anchors: bool):
    """프롬프트 입력만 끈 **사본**. 🔴 `bands`·`measured_by` 는 그대로다.

    「옆 등급 앵커 제거」는 앵커를 없애는 것이 아니라 **판정 등급·판정 조각의
    것만 남기는** 것이다 — `anchors_for` 가 이미 고르는 바로 그것이라,
    남는 앵커가 C0 에서 보이던 것과 **같은 한 줄**이다.
    """
    changes = {}
    if drop_rationale:
        changes["rationale"] = ""
    if drop_other_anchors:
        changes["anchors"] = criterion.anchors_for(grade, band_value)
    return dataclasses.replace(criterion, **changes) if changes else criterion


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--out", default="", help="기본값은 evidence_trace_<팔>.json")
    ap.add_argument("--only", default="",
                    help="이 항목 id 만 돈다 (재현 확인용)")
    args = ap.parse_args()

    drop_rationale, drop_other_anchors = ARMS[args.arm]
    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    judge = Judge()
    print(f"팔 {args.arm}: 취지 {'끔' if drop_rationale else '켬'} · "
          f"옆 등급 앵커 {'끔' if drop_other_anchors else '켬'}")
    print(f"백엔드: {judge.backend} · 모델: {judge.model_id}")
    judge.load()

    clips: dict[str, dict] = {}
    try:
        for key, rubric in sorted(rubrics.items()):
            items = []
            for criterion in rubric.criteria:
                if args.only and criterion.id != args.only:
                    continue
                for grade in (2, 1, 0):
                    for seg in range(len(criterion.bands[grade])):
                        for frac in FRACTIONS:
                            band_value = value_in_band(
                                criterion, grade, frac, seg)
                            features = {criterion.band_metric: band_value}
                            # 🔴 **원본 항목**으로 채운다 — 계기는 팔과 무관해야
                            #    한다 (사전 등록 2절).
                            features.update(
                                filler(criterion, grade, band_value, features))
                            got = criterion.grade_for(features)
                            if got != grade:
                                continue
                            shown = ablated(criterion, grade, band_value,
                                            drop_rationale, drop_other_anchors)
                            judged = judge.judge_criterion(
                                shown, features, rubric.sport)
                            # 🔴 등급은 **원본**으로 다시 확인한다. 사본이
                            #    판정을 움직였다면 그 자리에서 드러나야 한다.
                            if judged["grade"] != got:
                                raise SystemExit(
                                    f"{criterion.id} {band_value}: 등급이 움직였다 "
                                    f"({got} → {judged['grade']}) — 중단한다")
                            items.append({
                                "criterion_id": criterion.id,
                                "name": criterion.name,
                                "grade": grade,
                                "stored_grade": grade,
                                "segment": seg,
                                "band_value": band_value,
                                "evidence": judged.get("evidence", ""),
                                "metric_ref": judged.get("metric_ref", ""),
                                "given_metrics": select_metrics(criterion, features),
                            })
            if items:
                clips[key] = {"score": None, "grade": None, "items": items}
                print(f"  {key}: {len(items)}문장")
    finally:
        judge.unload()

    dest = HERE / (args.out or f"evidence_trace_{args.arm}.json")
    dest.write_text(json.dumps(
        {"tag": f"trace_{args.arm}", "arm": args.arm,
         "drop_rationale": drop_rationale,
         "drop_other_anchors": drop_other_anchors,
         "backend": judge.backend, "model": judge.model_id, "clips": clips},
        ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["items"]) for c in clips.values())
    print(f"\n{len(clips)}루브릭 {total}문장 → {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
