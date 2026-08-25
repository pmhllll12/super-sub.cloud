"""동작 확인 데모 — 영상 없이 실행 가능한 구간만 돌린다.

전체 파이프라인은 다음과 같다.

    영상 ──[A] 포즈 추출──▶ 키포인트 ──[B] 특징──▶ 측정값 ──[C] 판정──▶ 등급 ──[D] 합산──▶ 점수
         └─ 미검증 (실제 영상 없음) ─┘└──────────── 아래에서 실행 ────────────┘

[A]는 실제 클립이 없어 한 번도 실행된 적이 없다. 이 데모는 [A]의 출력 형식과
동일한 합성 키포인트를 입력으로 삼아 [B]~[D]를 실행한다. 따라서 이 데모가
통과한다고 해서 영상 분석이 동작한다는 뜻은 아니다.

    uv run python scripts/demo.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from supersub_agent.features import extract_features, verify_rubric_coverage  # noqa: E402
from supersub_agent.judge import Judge  # noqa: E402
from supersub_agent.scoring import aggregate, load_rubric  # noqa: E402
from test_features import build_sequence  # noqa: E402

BAR = "─" * 64


def main() -> None:
    print(BAR)
    print(" Super-Sub 자세 분석 에이전트 — 동작 데모")
    print(BAR)

    rubric = load_rubric(ROOT / "rubrics/football_instep_shot.yaml")
    print(f"\n[루브릭] {rubric.sport}/{rubric.motion} v{rubric.version}"
          f" — {len(rubric.criteria)}개 항목")
    for c in rubric.criteria:
        print(f"    {c.weight:>5.2f}  {c.name:<16} ← {', '.join(c.measured_by)}")
    if rubric.review_required:
        print("\n  ⚠️ 지도자 검수 전 임시 루브릭입니다. 각도 임계값은 확정값이 아닙니다.")

    # --- [A] 자리에 합성 데이터 ------------------------------------------
    print(f"\n{BAR}\n[A] 포즈 추출 — 건너뜀 (실제 영상 없음)")
    print("    아래는 pose.py가 내놓을 형식과 동일한 합성 키포인트입니다.")
    keypoints = build_sequence()
    print(f"    합성 키포인트: {keypoints.shape}  (프레임, 관절 17개, x/y/신뢰도)")

    # --- [B] 특징 산출 ----------------------------------------------------
    t0 = time.time()
    features = extract_features(keypoints)
    verify_rubric_coverage(rubric, features)
    print(f"\n[B] 특징 산출 — {time.time() - t0:.2f}초 (결정론적 계산)")
    for k, v in features.items():
        print(f"    {k:<48} {v}")

    # --- [C] 판정 ---------------------------------------------------------
    judge = Judge(model_size="1.2B")
    print(f"\n{BAR}\n[C] 판정 — {judge.model_id} 적재 중...")
    t0 = time.time()
    judge.load()
    print(f"    적재 완료 {time.time() - t0:.1f}초 (bf16, 양자화 없음)")

    scores = []
    try:
        for run in range(3):
            t0 = time.time()
            judgments = judge.judge_all(rubric, features)
            result = aggregate(judgments, rubric)
            scores.append(result["score"])
            print(f"    {run + 1}회차 → {result['score']}점 ({result['grade']})"
                  f"  {time.time() - t0:.1f}초")
            if run == 0:
                first = judgments
    finally:
        judge.unload()

    # --- 판정 근거 --------------------------------------------------------
    print(f"\n{BAR}\n[판정 근거] 1회차")
    for c in rubric.criteria:
        j = first[c.id]
        print(f"\n  {j['grade']}등급  {c.name}  (근거지표: {j['metric_ref']})")
        print(f"     근거: {j['evidence'][:150]}")

    # --- [D] 합산 ---------------------------------------------------------
    result = aggregate(first, rubric)
    print(f"\n{BAR}\n[D] 점수 합산 — 코드가 계산 (언어 모델 아님)")
    for b in result["breakdown"]:
        print(f"    {b['name']:<16} {b['grade']}등급 × 가중치 {b['weight']:.2f}"
              f" = {b['contribution']:>5.1f}점")
    print(f"    {'합계':<16} {result['score']}점 ({result['grade']})")

    sd = statistics.pstdev(scores)
    print(f"\n{BAR}\n[재현성] 3회 {scores}  표준편차 {sd:.2f}")
    print(f"    목표 3점 이내 — {'충족' if sd <= 3 else '미달'}")
    print(f"[표기] provisional={result['provisional']} "
          f"(검수 전 루브릭이므로 대외 노출 금지)")
    print(BAR)


if __name__ == "__main__":
    main()
