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
from pathlib import Path, PurePosixPath

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


def report_slug(key: str) -> str:
    """리포트를 놓을 자리 — **파일 이름만 쓰지 않는다.**

    옛 규칙은 파일 stem 하나였다. 그러면 프론트가 올리는
    `videos/<A>/clip.mp4` 와 `videos/<B>/clip.mp4` 가 **둘 다**
    `reports/clip/` 으로 가서 타임스탬프로만 갈린다 — 나중에 어느 업로드의
    결과인지 되짚을 수 없다(미결 17번에 고치겠다고 적어 둔 것이다).

    그래서 **바로 위 폴더를 함께 쓴다.** `videos/` 바로 아래 파일은 위 폴더가
    `videos` 뿐이므로 옛 경로를 그대로 유지한다 — 이미 올라간 리포트가
    떠내려가지 않는다.
    """
    parts = PurePosixPath(key).parts
    stem = PurePosixPath(key).stem
    parent = parts[-2] if len(parts) >= 2 else ""
    return f"{parent}/{stem}" if parent and parent != "videos" else stem


def owner_from_key(key: str) -> str | None:
    """`videos/<user_id>/…` 에서 소유자를 꺼낸다. 모양이 다르면 None.

    🔴 **파일 이름이 아니라 접두사에서 읽는다.** 미결 `jin` 24번이 키를
    `videos/<user_id>/<닉네임>-<원본이름>-<시각>-<video_id 앞 8자>.<ext>` 로
    바꾸기로 했는데 **`<user_id>/` 접두사는 그대로 둔다** — 소유 검사가 그
    접두사로 돌기 때문이다. 그래서 파일명 규칙이 바뀌어도 이 함수는 안 깨진다.
    파일명 끝의 8자는 `video_id` 의 **앞부분일 뿐**이라 자리를 정하는 데
    쓰면 안 된다.
    """
    parts = PurePosixPath(key).parts
    if len(parts) >= 3 and parts[0] == "videos":
        return parts[1]
    return None


def report_targets(
    out: str, key: str, video_id: str | None, stamp: str
) -> tuple[str, str]:
    """(리포트 URI, 미리보기를 놓을 접두사).

    계약(`jin` 24번)의 자리는 **영상 하나에 폴더 하나**다 —
    `reports/<user_id>/<video_id>/report.json` 과 같은 폴더의 미리보기.
    「저장」을 누르면 fastapi 가 원본을 `source.mp4` 로 **이 폴더에** 옮기므로,
    한 영상에 대한 것이 한자리에 모인다.

    🔴 **`video_id` 가 없으면 옛 자리를 그대로 쓴다.** 배치·평가 실행은
    백엔드 작업이 아니라 `video_id` 가 없고, 그때는 회차별 타임스탬프가 맞다 —
    같은 영상을 조건을 바꿔 여러 번 돌리는 것이 그쪽의 일상이다. 계약 자리로
    끌고 오면 앞 회차를 덮어써서 비교가 사라진다.

    🔴 **계약 자리에는 타임스탬프가 없다** — 재분석이 앞의 리포트를 덮는다.
    같은 영상의 최신 결과가 하나 있는 것이 계약의 뜻이고, 언제 낸 것인지는
    리포트 안의 `analyzed_at`·`code_version` 이 싣는다.
    """
    if video_id:
        owner = owner_from_key(key)
        base = f"{owner}/{video_id}" if owner else video_id
        return storage.join_uri(out, base, "report.json"), storage.join_uri(out, base)

    base = report_slug(key)
    return (
        storage.join_uri(out, base, f"{stamp}.json"),
        storage.join_uri(out, base, stamp),
    )


def resolve_videos(uri: str, region: str | None) -> list[str]:
    """인자로 받은 것이 파일이든 **폴더든** 분석할 영상 목록으로 바꾼다.

    🔴 **S3에는 폴더가 없다.** 콘솔이 폴더로 보여주는 `videos/<UUID>/` 는 그냥
    키 접두사이고, 그 접두사를 그대로 `download` 에 넘기면 "그런 키 없음"으로
    죽는다. 프론트가 `videos/<UUID>/<파일>.mp4` 로 올리므로 **폴더를 줬는데
    아무것도 안 돈다**가 그 증상이다.

    영상 확장자로 끝나면 객체 하나로 보고 그대로 쓴다. 아니면 접두사로 보고
    아래를 훑는다. 0바이트 객체(`videos/` 표식, 끊긴 업로드)는 빠진다.
    """
    if uri.lower().endswith(storage.VIDEO_SUFFIXES):
        return [uri]
    found = storage.find_videos(uri, region=region)
    if not found:
        raise SystemExit(
            f"영상을 찾지 못했다: {uri}\n"
            "  · 폴더라면 그 안에 영상 객체가 있는지 확인할 것 "
            "(0바이트 객체와 사이드카는 제외된다)\n"
            "  · 콘솔에 폴더로 보여도 실제 객체가 없을 수 있다 — 업로드가 "
            "중간에 끊기면 그렇게 남는다"
        )
    return found


def analyze_one(video: str, args, rubric, subject) -> str:
    """영상 한 편을 분석해 리포트를 올리고, **올린 자리를 돌려준다.**

    자리를 돌려주는 것은 워커가 완료 보고에 실어야 해서다(미결 `paik` 11번).
    🔴 **부르는 쪽이 자리를 다시 계산하게 두지 않는다** — 규칙(`report_targets`)이
    두 곳에 생기면 조용히 갈린다. 아는 쪽이 말해 주는 것이 맞다.
    """
    # --- 내려받기 --------------------------------------------------------
    # 임시 디렉터리에 받고 **끝까지 살려 둔다.** 미리보기 렌더링이 원본을 다시
    # 디코딩하기 때문이다(PoseResult가 프레임을 들고 있지 않으므로). 붙들고
    # 있는 것은 디스크지 RAM이 아니라 EBS 150GB에서는 값이 싸다 — 대신 4K
    # 300장(약 7GB)이 판정 내내 RAM에 남는 것을 피한다.
    with tempfile.TemporaryDirectory(prefix="supersub-") as tmp:
        _, key = storage.parse_s3_uri(video)
        local = Path(tmp) / Path(key).name
        t0 = time.time()
        storage.download(video, local, region=args.region)
        fetch_s = time.time() - t0
        size_mb = local.stat().st_size / 1e6
        print(f"[입력] {video} → {size_mb:.1f}MB, {fetch_s:.1f}초")

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
            result = aggregate(judgments, rubric, features=features)
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
        report_uri, preview_prefix = report_targets(
            args.out, storage.parse_s3_uri(video)[1], args.video_id, stamp
        )
        t0 = time.time()
        previews = build_previews(pose, int(features["impact_frame"]), Path(tmp))
        preview_s = time.time() - t0

        preview_uris: dict[str, str] = {}
        for kind, path in previews.items():
            uri = storage.join_uri(preview_prefix, path.name)
            storage.upload_file(path, uri, region=args.region)
            preview_uris[kind] = uri
            print(f"  미리보기 {kind}: {path.stat().st_size / 1e6:.2f}MB → {uri}")

    # --- 리포트 업로드 -----------------------------------------------------
    target = report_uri

    report = {
        # 🔴 **「저장」 뒤에는 이 키가 죽는다.** `jin` 24번의 `keep` 이 원본을
        # `reports/<user_id>/<video_id>/source.mp4` 로 옮기고 `videos/` 쪽을
        # 지우기 때문이다. 여기 값은 **분석 시점의 자리**이고, 옮긴 뒤의 자리를
        # 아는 것은 fastapi 뿐이다 — 그쪽에서 갱신하거나 리포트를 DB로 옮길 때
        # 정리한다(`jin` 24번에 적어 두었다).
        "source_video": video,
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
    return target




def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="s3://버킷/키(영상) 또는 s3://버킷/접두사(폴더)")
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
        "--video-id", default=None,
        help="백엔드의 video.id. 주면 리포트를 계약 자리 "
             "`<out>/<user_id>/<video_id>/report.json` 에 놓는다. "
             "🔴 주지 않으면 옛 자리(회차별 타임스탬프)를 쓴다 — 배치·평가용이다",
    )
    ap.add_argument(
        "--subject-box", default=None, metavar="x,y,w,h",
        help="분석할 사람의 **정규화 0~1** 박스. 사람이 화면에서 찍은 값이다. "
             "🔴 표시 해상도 픽셀이 아니다 — 주지 않으면 지금까지처럼 자동으로 고른다",
    )
    ap.add_argument(
        "--subject-at-ms", type=float, default=None,
        help="--subject-box 를 그린 영상 시각(밀리초). 박스를 주면 함께 주어야 한다",
    )
    ap.add_argument(
        "--result-json", default=None, metavar="경로",
        help="올린 리포트의 자리를 이 파일에 JSON 으로 남긴다. 워커가 완료 "
             "보고에 실으려고 읽는다(미결 `paik` 11번). 🔴 stdout 을 긁지 "
             "않는 것은 로그 문구가 바뀌면 조용히 깨지기 때문이다",
    )
    # 🔴 `--skip-analyzed` 를 **일부러 뺐다** (2026-09-08, 미결 jin 20번).
    #    `reports/` 유무로 "안 돈 것"을 가리는 것은 두 번째 큐였다. 큐의 정본은
    #    `analysis_job` 하나이고 그것을 소비하는 것은 `scripts/worker.py` 다.
    #    둘을 같이 두면 워커가 집어 `running` 으로 돌리는 사이 스캔이 같은 영상을
    #    또 돌린다 — `reports/` 는 분석이 **끝나야** 생기기 때문이다.
    #    되살리지 못하게 `tests/test_worker.py` 가 검사한다.
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

    videos = resolve_videos(video_uri := args.video, args.region)
    if len(videos) > 1 and args.video_id:
        # 🔴 한 폴더의 여러 편이 같은 자리에 리포트를 쓰면 **서로 덮는다.**
        #    계약 자리에는 타임스탬프가 없어서 마지막 것만 남는다.
        raise SystemExit(
            f"{video_uri} 아래에 영상이 {len(videos)}편인데 --video-id 가 하나다. "
            "video_id 는 영상 한 편의 것이므로 영상을 직접 지정할 것."
        )
    if len(videos) > 1 and subject is not None:
        raise SystemExit(
            f"{video_uri} 아래에 영상이 {len(videos)}편이다. 대상 지정"
            "(--subject-box)은 한 편에만 뜻이 있으므로 영상 하나를 직접 지정할 것."
        )

    print(f"대상 {len(videos)}편")
    failed = 0
    produced: list[dict[str, str]] = []
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] {video}")
        try:
            produced.append({"video": video,
                             "report_uri": analyze_one(video, args, rubric, subject)})
        except SystemExit as exc:
            # 🔴 영상을 **한 편만** 준 경우는 종료 코드를 그대로 올린다.
            #    워커(scripts/worker.py)가 이 코드 하나로 succeeded/failed 를
            #    가르기 때문이다 — 여기서 삼키면 품질 게이트에 걸린 분석이
            #    리포트도 없이 `succeeded` 로 보고된다. 2026-09-07 에 실제로
            #    그랬다(이 자리 주석은 "그대로 올라간다"고 말하고 있었지만
            #    코드는 삼키고 있었다).
            if len(videos) == 1:
                raise
            # 여러 편일 때는 한 편이 전체를 막지 않는다. 품질 게이트(종료 코드
            # 2)는 흔하고, 거기서 멈추면 뒤의 멀쩡한 영상이 영영 안 돈다.
            failed += 1
            print(f"  ✗ 건너뜀: {exc}")

    if failed:
        print(f"\n{failed}/{len(videos)}편 실패")
    # 🔴 여러 편 중 일부 실패는 0으로 끝낸다 — 스캔은 "돌 수 있는 것을 돌리는"
    #    작업이고, 한 편의 품질 미달로 스캔 전체가 실패가 되면 재시도가 무한히
    #    돈다. 한 편짜리 호출(위 raise)과는 뜻이 다르다.

    # 🔴 **성공한 것만 적는다.** 한 편짜리 호출이 실패하면 위에서 그대로
    #    올라가 여기 못 온다 — 그래서 실패한 작업의 파일은 아예 안 생기고,
    #    워커는 "없으면 안 싣는다"로 읽으면 된다.
    if args.result_json:
        Path(args.result_json).write_text(
            json.dumps({"reports": produced}, ensure_ascii=False), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
