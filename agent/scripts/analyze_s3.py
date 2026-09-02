"""S3 영상 1건 분석 — 내려받기 → 측정 → 판정 → 리포트 업로드.

    uv run python scripts/analyze_s3.py s3://버킷/videos/pitch01.mp4 \
        --rubric rubrics/baseball_pitching.yaml \
        --out s3://버킷/reports \
        --side left

analyze.py의 S3판이다. 측정·판정 절차는 같고 입력을 S3에서 받고 산출물을 S3로
되돌려 놓는 것만 다르다.

**판정 백엔드는 이 스크립트가 고르지 않는다.** 환경변수 SUPERSUB_VLLM_URL이
있으면 Judge가 vLLM으로 가고, 없으면 로컬 적재다 (judge.py 참고). EC2에서는
systemd 유닛이 그 변수를 준다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent import storage  # noqa: E402
from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    extract_features,
    verify_rubric_coverage,
)
from supersub_agent.judge import Judge  # noqa: E402
from supersub_agent.pose import DEFAULT_TARGET_FPS, extract_keypoints  # noqa: E402
from supersub_agent.scoring import aggregate, load_rubric  # noqa: E402


def code_version() -> str:
    """리포트에 남길 코드 버전.

    수동 배포(git pull origin ho)라 EC2의 코드가 어느 시점인지 리포트만 보고는
    알 수 없다. 커밋을 같이 실으면 이상한 결과가 나왔을 때 어느 코드가 냈는지
    되짚을 수 있다.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=5, check=True,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="s3://버킷/키 형식의 원본 영상")
    ap.add_argument("--rubric", default="rubrics/football_instep_shot.yaml")
    ap.add_argument("--model", default="1.2B", choices=["1.2B", "2.4B", "7.8B"])
    ap.add_argument(
        "--out", required=True,
        help="리포트를 올릴 s3:// 접두사 (예: s3://버킷/reports)",
    )
    ap.add_argument(
        "--side", default="auto", choices=["auto", "left", "right"],
        help="스윙 측(던지는 팔·차는 발). 루브릭의 impact_limb에만 적용된다",
    )
    ap.add_argument("--fps", type=int, default=DEFAULT_TARGET_FPS)
    ap.add_argument("--region", default=None, help="S3 리전 (미지정 시 기본 설정)")
    args = ap.parse_args()

    if not storage.is_s3_uri(args.video) or not storage.is_s3_uri(args.out):
        raise SystemExit("video와 --out은 모두 s3:// 형식이어야 한다.")

    rubric = load_rubric(args.rubric)
    print(f"루브릭: {rubric.sport}/{rubric.motion} v{rubric.version} "
          f"({len(rubric.criteria)}개 항목)")

    # --- 내려받기 --------------------------------------------------------
    # 임시 디렉터리에 받는다. g4dn.xlarge의 EBS를 원본 영상으로 채우면
    # 모델 캐시(수 GB)와 자리를 다투므로 분석이 끝나면 지운다.
    with tempfile.TemporaryDirectory(prefix="supersub-") as tmp:
        _, key = storage.parse_s3_uri(args.video)
        local = Path(tmp) / Path(key).name
        t0 = time.time()
        storage.download(args.video, local, region=args.region)
        fetch_s = time.time() - t0
        size_mb = local.stat().st_size / 1e6
        print(f"[입력] {args.video} → {size_mb:.1f}MB, {fetch_s:.1f}초")

        # --- 측정 (결정론적) ---------------------------------------------
        t0 = time.time()
        try:
            # observe=False — 배치 분석은 서비스 입력이 아니다. 기본값 True로
            # 두면 이 실행이 서비스 입력 분포 관측에 섞인다.
            pose = extract_keypoints(local, target_fps=args.fps, observe=False)
            features = extract_features(
                pose.keypoints, pose.objects, rubric.impact_limb,
                rubric.impact_event, args.side,
            )
        except InsufficientQuality as exc:
            print(f"\n분석 중단: {exc}")
            raise SystemExit(2) from exc
        measure_s = time.time() - t0

        verify_rubric_coverage(rubric, features)
        print(f"[측정] {len(pose.keypoints)}프레임 "
              f"(실효 {pose.sampled_fps:.2f}fps), swing_side={args.side}, "
              f"{measure_s:.1f}초")

    # --- 판정 -------------------------------------------------------------
    # 임시 디렉터리 밖이다. PoseResult는 원본 프레임을 들고 있지 않으므로
    # (pose.PoseResult 참고) 영상 파일을 지운 뒤에도 keypoints를 쓸 수 있고,
    # 4K 원본을 판정이 끝날 때까지 붙들지 않는다. load_frames()를 부르면
    # 파일이 없어 실패하므로 여기서는 부르지 않는다.
    judge = Judge(model_size=args.model)
    t0 = time.time()
    judge.load()
    print(f"[판정] 백엔드 {judge.backend} ({judge.model_id}), "
          f"준비 {time.time() - t0:.1f}초")

    t0 = time.time()
    try:
        judgments = judge.judge_all(rubric, features)
        result = aggregate(judgments, rubric)
    finally:
        judge.unload()
    judge_s = time.time() - t0

    for item in result["breakdown"]:
        print(f"  {item['grade']}등급  {item['name']:<16} {item['evidence']}")
    print(f"\n총점 {result['score']}점 ({result['grade']})"
          f"{'  [provisional]' if result['provisional'] else ''}")

    # --- 리포트 업로드 -----------------------------------------------------
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem = Path(storage.parse_s3_uri(args.video)[1]).stem
    target = storage.join_uri(args.out, stem, f"{stamp}.json")

    report = {
        "source_video": args.video,
        "analyzed_at": stamp,
        "code_version": code_version(),
        "rubric": {
            "sport": rubric.sport, "motion": rubric.motion,
            "version": rubric.version, "path": args.rubric,
            "impact_limb": rubric.impact_limb,
            "impact_event": rubric.impact_event,
        },
        # swing_side는 impact_limb에만 적용된다 — 반대쪽 사지 지표는 auto
        # 판별로 나온 값이다 (features.extract_features 참고).
        "swing_side": args.side,
        "target_fps": args.fps,
        "sampled_fps": round(float(pose.sampled_fps), 2),
        "frames": int(len(pose.keypoints)),
        "judge_backend": judge.backend,
        "judge_model": judge.model_id,
        "timing": {
            "fetch_s": round(fetch_s, 2),
            "measure_s": round(measure_s, 2),
            "judge_s": round(judge_s, 2),
        },
        "features": features,
        "result": result,
    }
    storage.upload_json(report, target, region=args.region)
    print(f"\n저장: {target}")
    print(json.dumps(report["timing"], ensure_ascii=False))


if __name__ == "__main__":
    main()
