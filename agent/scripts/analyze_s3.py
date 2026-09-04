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
import base64
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
    frame_metrics_as_seconds,
    verify_rubric_coverage,
)
from supersub_agent.judge import Judge  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    DEFAULT_TARGET_FPS,
    crop_to_person,
    draw_overlay,
    encode_preview,
    extract_keypoints,
    parse_subject_spec,
    render_tracked_clip,
    subject_envelope,
)
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


def build_previews(pose, impact: int, work: Path) -> dict[str, Path]:
    """스켈레톤 미리보기 두 장을 만든다 — 임팩트 정지화면과 추적 영상.

    **판정이 끝난 뒤에 부른다.** PoseResult가 프레임을 들고 있지 않은 것이 바로
    이것 때문이다(pose.PoseResult 참고) — 4K 300장이면 약 7GB라, 포즈 추출부터
    판정 모델 적재까지 내내 들고 있으면 호스트 RAM이 먼저 터진다(미결 9번).
    여기서 재디코딩하는 비용은 포즈 추출의 10% 수준이다.

    추가 추론이 없다. 이미 얻은 키포인트로 그리기만 한다 — 그림에 나오는 것은
    ViTPose가 낸 관절이고, YOLO는 이 경로에 없다.

    실패해도 분석을 막지 않는다. 미리보기는 검수 편의지 산출물의 본체가 아니다.
    """
    out: dict[str, Path] = {}
    frames = pose.load_frames()
    if not frames:
        return out

    try:
        if 0 <= impact < len(frames):
            kps = pose.keypoints[impact]
            uri = encode_preview(crop_to_person(draw_overlay(frames[impact], kps), kps))
            still = work / "impact.jpg"
            still.write_bytes(base64.b64decode(uri.split(",", 1)[1]))
            out["impact_image"] = still

        clip = work / "tracked.webm"
        render_tracked_clip(
            frames, pose.keypoints, clip, pose.sampled_fps, impact=impact
        )
        out["tracked_video"] = clip
    except Exception as exc:  # noqa: BLE001 — 미리보기 실패가 분석을 막지 않는다
        print(f"  ⚠️ 미리보기 생성 실패 ({type(exc).__name__}: {exc}) — 계속한다")

    return out


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
    ap.add_argument(
        "--subject-box", default=None, metavar="x,y,w,h",
        help="분석할 사람의 **정규화 0~1** 박스. 사람이 화면에서 찍은 값이다. "
             "🔴 표시 해상도 픽셀이 아니다 — 주지 않으면 지금까지처럼 자동으로 고른다",
    )
    ap.add_argument(
        "--subject-at-ms", type=float, default=None,
        help="--subject-box 를 그린 영상 시각(밀리초). 박스를 주면 함께 주어야 한다",
    )
    args = ap.parse_args()

    if not storage.is_s3_uri(args.video) or not storage.is_s3_uri(args.out):
        raise SystemExit("video와 --out은 모두 s3:// 형식이어야 한다.")

    # 규칙은 pose.parse_subject_spec 하나뿐이다 — HTTP도 같은 것을 쓴다.
    # 여기서는 오류를 종료 코드로 옮기기만 한다.
    try:
        subject = parse_subject_spec(args.subject_box, args.subject_at_ms)
    except ValueError as exc:
        raise SystemExit(f"대상 지정이 잘못됐다: {exc}") from exc

    rubric = load_rubric(args.rubric)
    print(f"루브릭: {rubric.sport}/{rubric.motion} v{rubric.version} "
          f"({len(rubric.criteria)}개 항목)")

    # --- 내려받기 --------------------------------------------------------
    # 임시 디렉터리에 받고 **끝까지 살려 둔다.** 미리보기 렌더링이 원본을 다시
    # 디코딩하기 때문이다(PoseResult가 프레임을 들고 있지 않으므로). 붙들고
    # 있는 것은 디스크지 RAM이 아니라 EBS 150GB에서는 값이 싸다 — 대신 4K
    # 300장(약 7GB)이 판정 내내 RAM에 남는 것을 피한다.
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
            pose = extract_keypoints(
                local, target_fps=args.fps, observe=False, subject=subject
            )
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

        # --- 판정 ---------------------------------------------------------
        # 프레임은 여기서도 메모리에 없다 — PoseResult가 키포인트만 들고 있다.
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

        # --- 미리보기 ------------------------------------------------------
        # 판정이 끝난 뒤다. 프레임을 다시 디코딩하므로 판정 모델과 겹치지 않는다.
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        stem = Path(storage.parse_s3_uri(args.video)[1]).stem
        t0 = time.time()
        previews = build_previews(pose, int(features["impact_frame"]), Path(tmp))
        preview_s = time.time() - t0

        preview_uris: dict[str, str] = {}
        for kind, path in previews.items():
            uri = storage.join_uri(args.out, stem, stamp, path.name)
            storage.upload_file(path, uri, region=args.region)
            preview_uris[kind] = uri
            print(f"  미리보기 {kind}: {path.stat().st_size / 1e6:.2f}MB → {uri}")

    # --- 리포트 업로드 -----------------------------------------------------
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
        # 프레임 단위 지표를 초로 (미결 7번 E-3). `sampled_fps`가 바로 위에
        # 있어도 읽는 쪽이 나눠 주기를 기대하면 안 된다 — 어느 것이 인덱스이고
        # 어느 것이 길이인지는 features 모듈만 안다.
        "frame_metrics_seconds": frame_metrics_as_seconds(
            features, float(pose.sampled_fps)
        ),
        "judge_backend": judge.backend,
        "judge_model": judge.model_id,
        # 스켈레톤은 ViTPose 키포인트로 그린 것이다 — 추가 추론이 없고
        # YOLO는 이 경로에 없다. 비어 있으면 렌더링에 실패한 것이고,
        # 그래도 위의 측정·판정은 그대로 유효하다.
        "previews": preview_uris,
        "timing": {
            "fetch_s": round(fetch_s, 2),
            "measure_s": round(measure_s, 2),
            "judge_s": round(judge_s, 2),
            "preview_s": round(preview_s, 2),
        },
        # **누구를** 분석했는지 — 지정/자동/폴백과 선택 박스 시계열.
        # 🔴 폴백을 조용히 넘기지 않는다. 이것이 없으면 "찍은 사람이 실제로
        # 분석됐는가"를 사후에 확인할 방법이 없다 (미결 18번).
        "subject": subject_envelope(pose, int(len(pose.keypoints))),
        "features": features,
        "result": result,
    }
    storage.upload_json(report, target, region=args.region)
    print(f"\n저장: {target}")
    print(json.dumps(report["timing"], ensure_ascii=False))


if __name__ == "__main__":
    main()
