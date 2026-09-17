"""`player_vector` 의 **축을 무엇으로 잡을 것인가** — 세 후보의 실측 (미결 `ho` 32번·`jin` 28번).

🔴 **이것은 사전 등록된 실험이 아니라 descriptive 계수다.** 가설도 합격선도
없고, 아래 숫자를 보고 설계를 고른 것이 아니다 — 축 선택의 근거는 **구조적인
것**(등급은 3단계라 방향을 잃는다)이고 이 스크립트는 그 구조가 실제 데이터에서
얼마나 나타나는지를 **세어 볼 뿐**이다. 판정 문장을 쓰지 않는 이유가 그것이다.

세는 것 셋 (같은 클립 집합에서):

    (A) 측정 지표값   — 연속. 물리 단위가 섞여 있다(각도·비율·프레임)
    (B) 항목별 등급   — 0/1/2 이산
    (C) 항목별 stat   — 연속 0~100, 이미 공통 축으로 눌러 놓은 값

읽는 자료는 **이미 측정된 것**이다 (`eval/pending21_hip_rotation/`의 축구 경로
산출). 영상도 GPU 도 다시 쓰지 않고, production 의 `Criterion.grade_for` ·
`score_for` 를 **import 만** 한다.

    cd agent && uv run python eval/pending32_vector_basis/count_bases.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import load_rubric  # noqa: E402

RUBRIC = ROOT / "rubrics" / "football_instep_shot.yaml"
SOURCE = ROOT / "eval" / "pending21_hip_rotation" / "before_rubric_clips.csv"


def main() -> None:
    rubric = load_rubric(str(RUBRIC))
    metrics = sorted({m for c in rubric.criteria for m in c.measured_by})

    rows = [
        r
        for r in csv.DictReader(SOURCE.open(encoding="utf-8"))
        # 🔴 selector 조합마다 행이 하나씩 있다 — baseline 쌍만 취하지 않으면
        #    같은 클립을 다섯 번 세고 「고유 벡터」가 부풀지 않는 대신 분모가 는다.
        if r["rubric"] == "football/instep_shot"
        and r["features_ok"] == "1"
        and r["production_selector"] == "baseline"
        and r["comparison_selector"] == "baseline"
    ]
    print(f"축구 인스텝 클립 {len(rows)}편 · 루브릭 항목 {len(rubric.criteria)}개 "
          f"· 그 항목들이 쓰는 지표 {len(metrics)}개")

    print("\n지표별 실측 보유율 — 🔴 루브릭이 「쓴다」와 「실제로 재진다」는 다르다")
    present = {}
    for m in metrics:
        present[m] = sum(1 for r in rows if r.get(m) not in (None, ""))
        print(f"  {m:45s} {present[m]:2d}/{len(rows)}")

    # 전 클립에서 한 번도 안 잡힌 지표는 축으로 잡을 수 없다 — 그 칸은
    # 「0 인 차원」이 아니라 **없는 차원**이다.
    usable = [m for m in metrics if present[m] > 0]
    dropped = [m for m in metrics if present[m] == 0]
    if dropped:
        print(f"\n🔴 한 번도 안 잡힌 지표 {len(dropped)}개 — 축에서 뺀다: {dropped}")
    criteria = [c for c in rubric.criteria if set(c.measured_by) <= set(usable)]

    bases: dict[str, set] = {"A 지표값": set(), "B 등급": set(), "C stat": set()}
    complete = 0
    for r in rows:
        if any(r.get(m) in (None, "") for m in usable):
            continue
        complete += 1
        f = {m: float(r[m]) for m in usable}
        bases["A 지표값"].add(tuple(round(f[m], 4) for m in usable))
        bases["B 등급"].add(tuple(c.grade_for(f) for c in criteria))
        bases["C stat"].add(tuple(round(c.score_for(f), 2) for c in criteria))

    print(f"\n전 축이 채워진 클립 {complete}/{len(rows)}편 "
          f"(항목 {len(criteria)}개 · 지표 {len(usable)}개)")
    print("고유 벡터 수 — 같으면 두 선수가 벡터로 구분되지 않는다")
    for name, seen in bases.items():
        collided = complete - len(seen)
        print(f"  ({name:8s}) {len(seen):2d}/{complete}"
              + (f"  🔴 겹친 클립 {collided}편" if collided else ""))


if __name__ == "__main__":
    main()
