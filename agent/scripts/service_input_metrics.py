"""축적된 서비스 입력 관측 레코드로 입력 분포를 낸다.

    uv run python scripts/service_input_metrics.py [--sink PATH] [--csv OUT.csv]

**여기서 나오는 값은 입력 노출과 측정 동작이지 대상 선택의 정확성이 아니다.**
다중인원 비율이 높다는 것은 "화면에 사람이 여럿인 상황이 많다"는 뜻이지
"어떤 selector가 더 낫다"는 뜻이 아니다.

레코드가 없으면 숫자를 만들지 않고 그 사실을 그대로 알린다.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent import observability as obs  # noqa: E402

# fps 구간 — 관측용 표시 구간일 뿐 제품 기준이 아니다.
FPS_BUCKETS = [(0, 15, "<15"), (15, 25, "15-24"), (25, 30, "25-29"),
               (30, 60, "30-59"), (60, float("inf"), ">=60")]


def bucket(v: float | None) -> str:
    if v is None:
        return "unknown"
    for lo, hi, name in FPS_BUCKETS:
        if lo <= v < hi:
            return name
    return "unknown"


def _report_redirects(origin: str) -> None:
    """0건일 때, **다른 sink로 기록된 적이 있는지**를 알려 준다.

    2026-08-31의 혼선이 정확히 이 자리였다 — 개발 확인용으로 sink를 /tmp로
    돌려 둔 상태에서 프로덕션 경로로 3건이 돌았는데, 나중에 환경변수 없이 읽고
    "서비스 분석 0건"으로 결론지었다. 그때 환경변수는 이미 사라진 뒤라 되짚을
    단서가 없었다. 기본 위치에 남긴 흔적이 그 단서다.
    """
    marks = obs.load_redirects()
    if not marks:
        if origin == "default":
            print("  우회 흔적도 없다 — 정말 분석이 없었을 가능성이 높다.")
        return
    print()
    print(f"  🔴 다른 sink로 기록된 적이 있다 ({len(marks)}회). 0건을 "
          "'분석이 없었다'로 읽으면 안 된다:")
    for m in marks[-5:]:
        print(f"     {m.get('at', '?')}  →  {m.get('sink', '?')}"
              f"  (출처 {m.get('origin', '?')}, pid {m.get('pid', '?')})")
    if len(marks) > 5:
        print(f"     … 그 외 {len(marks) - 5}회. 전체는 {obs.REDIRECT_LOG}")
    print("  그 경로를 --sink 로 지정해 다시 볼 것.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sink", default=None, help="JSONL 경로 (기본: 환경변수/기본 sink)")
    ap.add_argument("--csv", default=None, help="클립 단위 표를 CSV로 저장")
    args = ap.parse_args()

    # 어느 sink를 읽는지는 **항상** 먼저 밝힌다. 숫자만 보고 "서비스 전체"로
    # 읽으면 우회된 파일의 부분집합을 전체로 오해한다.
    path, origin = obs.resolve_sink(args.sink)
    label = {"argument": "--sink 인자", "env": "SUPERSUB_METRICS_SINK 환경변수",
             "default": "기본 위치"}[origin]
    print(f"sink: {path}  ({label})")
    if origin != "default":
        print("  ⚠ 기본 위치가 아니다 — 여기 숫자는 이 파일에 기록된 분석만 담는다.")
    print()

    recs = obs.load(args.sink)
    if not recs:
        # "sink가 없다"와 "sink는 있는데 비어 있다"를 구분한다 — 전자는 아직
        # 분석이 없었다는 뜻이고, 후자는 기록 경로가 고장났을 수 있다는 뜻이다.
        print("SERVICE_INPUT_AVAILABLE = FALSE")
        if not path.exists():
            print(f"  sink 파일이 없다: {path}")
            print("  분석이 한 건도 수행되지 않았거나 sink 경로가 다르다.")
        else:
            print(f"  sink는 있으나 유효한 레코드가 0건이다: {path}")
            print(f"  파일 크기 {path.stat().st_size}바이트 — 기록 경로가 고장났을 수 있다.")
        _report_redirects(origin)
        print("  숫자를 만들지 않는다.")
        return 1

    agg = obs.aggregate(recs)
    print("SERVICE_INPUT_AVAILABLE = TRUE\n")

    print("표 1 — 서비스 입력 전체 분포")
    print(f"  total clips                        {agg['total_clips']}")
    print(f"  total analyzed frames              {agg['total_analyzed_frames']}")
    print(f"  frames with 0 candidate            {agg['frames_with_0_person']}")
    print(f"  frames with 1 candidate            {agg['frames_with_1_person']}")
    print(f"  frames with >=2 candidates         {agg['frames_with_ge2_person']}")
    print(f"  multi-person frame ratio           {agg['multi_person_frame_ratio']:.4f}")
    print(f"  clips with any multi-person frame  {agg['clips_with_any_multi_person']}"
          f" / {agg['total_clips']}")
    print(f"  median source fps                  {agg['median_source_fps']}")
    print(f"  median sampled fps                 {agg['median_sampled_fps']}")
    print(f"  median analyzed frame count        {agg['median_analyzed_frame_count']}")

    print("\n표 2 — candidate count distribution")
    total = agg["total_analyzed_frames"]
    for k, v in agg["candidate_count_histogram"].items():
        print(f"  {k:>3}  {v:6d}  {v / total:6.2%}" if total else f"  {k:>3}  {v}")

    print("\n표 3 — fps distribution (clips)")
    for label, key in (("source", "source_fps"), ("sampled", "sampled_fps")):
        counts: dict[str, int] = {}
        for r in recs:
            counts[bucket(r.get(key))] = counts.get(bucket(r.get(key)), 0) + 1
        print(f"  [{label}] " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    print("\n클립 단위 multi-person exposure (raw ratio — 제품 기준 아님)")
    for r in sorted(recs, key=lambda x: -x.get("multi_person_frame_ratio", 0))[:20]:
        print(f"  {r['analysis_id'][:12]}  frames {r['analyzed_frame_count']:4d}  "
              f"ratio {r['multi_person_frame_ratio']:.3f}  "
              f"max_cand {r['max_candidate_count']}  "
              f"src_fps {r['source_fps']}  sampled_fps {r['sampled_fps']}")

    if args.csv:
        cols = ["analysis_id", "analyzed_at", "rubric_key", "source_fps", "sampled_fps",
                "analyzed_frame_count", "frames_with_0_person", "frames_with_1_person",
                "frames_with_2_person", "frames_with_3plus_person",
                "frames_with_ge2_person", "multi_person_frame_ratio",
                "max_candidate_count"]
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(recs)
        print(f"\n클립 단위 표를 적었다: {args.csv}")

    print("\n주의: 위 값은 input exposure / measurement behavior이며 "
          "target correctness가 아니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
