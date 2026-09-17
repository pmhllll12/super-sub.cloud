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

import argparse
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


def value_in_band(criterion, grade: int, frac: float, seg: int = 0) -> float:
    """등급 `grade` 의 `seg` 번째 조각 안에서 값 하나를 고른다.

    🔴 **`seg` 는 2026.09.17 에 더했다.** 그전에는 `bands[grade][0]` — **첫
    조각만** 뽑았고, 그래서 양방향 구간 **8곳의 두 번째 조각을 한 번도 물어본
    적이 없다.** 방향 오독을 재는 회차인데 **방향의 한쪽만 재고 있었다**
    (사전 등록 `PREREGISTRATION_plain.md` 3절).
    """
    lo, hi = criterion.bands[grade][seg]
    if lo is None:
        return round(float(hi) * frac, 1)
    if hi is None:
        return round(float(lo) + 2.0 + 8.0 * frac, 1)
    return round(float(lo) + (float(hi) - float(lo)) * frac, 1)


def filler(criterion, grade: int, band_value: float, given: dict) -> dict:
    """밴드 지표가 **아닌** 값을 무엇으로 채울까 (미결 23번 A).

    🔴 **상수 `10.0` 을 쓰던 자리다. 그것이 문장을 끌고 갔다.**
    실측 중앙은 4프레임인데 10.0 은 프롬프트 앵커(잘함 4·아쉬움 1)를 넘어
    **「길다」로 읽혔고**, 굴곡 4.8 의 오독이 지속 1·4 에서는 안 났다
    (`RESULTS_second_metric.md`). 계기가 만든 결함이다.

    대신 **그 등급 앵커의 값**을 쓴다. 루브릭이 이미 등급마다 적어 둔 값이라
    실측에서 왔고, 등급과 어긋나지 않으며, **결정적이다**(무작위면 재현이
    깨지고, 중앙값 하나면 또 상수라 같은 형태의 결함이다).

    앵커가 여럿이면 **가-3 과 같은 규칙** — 밴드 값이 앉은 조각의 앵커를 쓴다.

    🔴 **이 표본은 이제 「두 번째 지표가 등급과 어긋날 때」를 못 잰다.**
    그건 일부러다 — 그 질문은 `second_metric.py` 가 따로 재고, 한 표본이
    둘을 겸하게 두는 것이 바로 지금 고치는 문제다. **계기는 중립이어야 한다.**
    """
    rest = [c for c in criterion.measured_by if c != criterion.band_metric]
    if not rest:
        return {}
    anchors = criterion.anchors_for(grade, band_value)
    out = {}
    for code in rest:
        for anchor in anchors:
            if code in anchor["measured"]:
                out[code] = float(anchor["measured"][code])
                break
        else:
            raise SystemExit(
                f"{criterion.id} {grade}등급 앵커에 {code} 가 없다 — "
                "채울 값의 출처가 없다. 앵커에 적을 것 (사전 등록 3절)."
            )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence_football.json",
                    help="낼 파일 이름 (before/after 를 따로 둘 때 쓴다)")
    args = ap.parse_args()

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
                    # 🔴 **조각마다** 돈다 — 양방향 구간의 반대쪽을 안 뽑으면
                    #    방향 오독을 반쪽만 재게 된다 (사전 등록 3절).
                    for seg in range(len(criterion.bands[grade])):
                        for frac in FRACTIONS:
                            band_value = value_in_band(
                                criterion, grade, frac, seg)
                            features = {criterion.band_metric: band_value}
                            # 밴드 지표 말고 `measured_by` 에 있는 것도 채운다 —
                            # 프롬프트가 그것들도 보여주기 때문이다.
                            features.update(
                                filler(criterion, grade, band_value, features))
                            got = criterion.grade_for(features)
                            if got != grade:
                                continue  # 고른 값이 그 등급이 아니면 버린다
                            judged = judge.judge_criterion(
                                criterion, features, rubric.sport)
                            items.append({
                                "criterion_id": criterion.id,
                                "name": criterion.name,
                                "grade": grade,
                                "stored_grade": grade,
                                # 어느 조각에서 뽑은 값인가 — 판독이 이걸로
                                # 「반대 조각의 말을 썼는가」를 가른다.
                                "segment": seg,
                                "evidence": judged.get("evidence", ""),
                                "metric_ref": judged.get("metric_ref", ""),
                                "given_metrics": select_metrics(criterion, features),
                            })
            clips[key] = {"score": None, "grade": None, "items": items}
            print(f"  {key}: {len(items)}문장")
    finally:
        judge.unload()

    dest = HERE / args.out
    dest.write_text(json.dumps(
        {"tag": "football", "backend": judge.backend, "model": judge.model_id,
         "clips": clips}, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["items"]) for c in clips.values())
    print(f"\n{len(clips)}루브릭 {total}문장 → {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
