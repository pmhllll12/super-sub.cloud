"""영상 1건 분석 — 측정 → 판정 → 합산 전 구간 실행.

    uv run python scripts/analyze.py data/shot01.mp4
    uv run python scripts/analyze.py data/shot01.mp4 --repeat 5   # 재현성 확인

8GB VRAM 제약 때문에 포즈 모델과 판정 모델을 동시에 올리지 않는다.
포즈 추출을 모두 끝내고 GPU를 비운 뒤 판정 모델을 적재한다.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    extract_features,
    verify_rubric_coverage,
)
from supersub_agent.judge import Judge  # noqa: E402
from supersub_agent.pose import extract_keypoints  # noqa: E402
from supersub_agent.scoring import aggregate, load_rubric  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--rubric", default="rubrics/football_instep_shot.yaml")
    ap.add_argument("--model", default="1.2B", choices=["1.2B", "2.4B", "7.8B"])
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument(
        "--repeat", type=int, default=1,
        help="같은 측정값으로 판정을 N회 반복해 재현성을 확인한다.",
    )
    args = ap.parse_args()

    rubric = load_rubric(args.rubric)
    print(f"루브릭: {rubric.sport}/{rubric.motion} v{rubric.version} "
          f"({len(rubric.criteria)}개 항목)")
    if rubric.review_required:
        print("  ⚠️ 지도자 검수 전 임시 루브릭 — 결과는 provisional로 표기됩니다.\n")

    # --- 측정 (결정론적) ------------------------------------------------
    t0 = time.time()
    try:
        # observe=False — CLI는 서비스 입력이 아니다. 개발 중 반복 실행이
        # 서비스 입력 분포에 섞이면 그 분포로 내리는 판단이 오염된다.
        pose = extract_keypoints(args.video, target_fps=args.fps, observe=False)
        # 임팩트 정의와 도구 궤적을 루브릭에서 받아 넘긴다. 넘기지 않으면 팔
        # 루브릭도 다리로 측정되고, 도구 기반 항목이 통째로 빠진다.
        features = extract_features(
            pose.keypoints, pose.objects, rubric.impact_limb, rubric.impact_event
        )
    except InsufficientQuality as exc:
        print(f"\n분석 중단: {exc}")
        raise SystemExit(2) from exc
    measure_s = time.time() - t0

    verify_rubric_coverage(rubric, features)
    print(f"[측정] {len(pose.keypoints)}프레임, {measure_s:.1f}초")
    print(json.dumps(features, ensure_ascii=False, indent=2))

    # --- 판정 (언어 모델) -----------------------------------------------
    judge = Judge(model_size=args.model)
    t0 = time.time()
    judge.load()
    load_s = time.time() - t0
    print(f"\n[판정] 모델 적재 {load_s:.1f}초 ({judge.model_id})")

    scores = []
    result = None
    try:
        for run in range(args.repeat):
            t0 = time.time()
            judgments = judge.judge_all(rubric, features)
            result = aggregate(judgments, rubric)
            scores.append(result["score"])
            print(f"  {run + 1}회차: {result['score']}점 "
                  f"({result['grade']}) — {time.time() - t0:.1f}초")
    finally:
        judge.unload()

    # --- 결과 ------------------------------------------------------------
    print("\n" + "=" * 60)
    for item in result["breakdown"]:
        print(f"  {item['grade']}등급  {item['name']:<16} {item['evidence']}")
    print(f"\n총점 {result['score']}점 ({result['grade']})"
          f"{'  [provisional]' if result['provisional'] else ''}")

    if args.repeat > 1:
        sd = statistics.pstdev(scores)
        print(f"\n재현성: {args.repeat}회 {scores}  표준편차 {sd:.2f}")
        print(f"  기준 3점 이내 — {'충족' if sd <= 3 else '미달'}")

    out = Path("out") / f"{args.video.stem}_result.json"
    out.write_text(
        json.dumps({"features": features, "result": result}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
