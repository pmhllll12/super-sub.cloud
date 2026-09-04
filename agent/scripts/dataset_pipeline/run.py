#!/usr/bin/env python3
"""순환형 배치 파이프라인 — 받고 · 재고 · 치우고 · 다음 100개.

    uv run python -m scripts.dataset_pipeline.run --sport soccer \
        --rubric rubrics/football_instep_shot.yaml --batches 1 --limit 20

한 배치가 도는 순서:

    1  D드라이브에 현재 배치(기본 100개)를 받는다
    2  포즈를 뽑고 지표를 낸다 (`--stage full` 이면 판정까지)
    3  원본을 정리한다 — 지우거나, S3에 올린 뒤 지우거나, 남긴다
    4  커서를 옮기고 다음 배치로

## 🔴 이 파이프라인이 만드는 것은 **측정이지 정확도가 아니다**

여기서 나온 지표에는 **정답이 없다.** 세 데이터셋 어느 것도 자세 정답을 달고
있지 않다(이벤트·판정 라벨뿐). 그래서 결과를 보고 "정확해졌다"고 쓰면 안 된다 —
`/labels/` 문서가 정리한 네 층 중 어느 층도 이 데이터로는 안 열린다.

## 🔴 기존 평가셋(39클립)과 섞지 않는다

B-1~B-6 은 Kinetics 39클립 위에서 나온 값이다. 여기 결과는 **다른 모집단의
새 측정**이지 그 재실행이 아니다. 산출물을 `<root>/<종목>/results/` 에 따로 두고
`agent/eval/` 에 넣지 않는 이유가 그것이다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# `python -m scripts.dataset_pipeline.run` 로 부르면 저장소 루트가 sys.path 에
# 들어오지만, 파일로 직접 부를 수도 있어 src/ 를 명시적으로 얹는다.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scripts.dataset_pipeline import config, lifecycle, sources  # noqa: E402
from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    extract_features,
    frame_metrics_as_seconds,
    verify_rubric_coverage,
)
from supersub_agent.scoring import load_rubric  # noqa: E402


def analyze_one(video: Path, rubric, stage: str, side: str) -> dict:
    """클립 하나 — 포즈 추출 + 지표. `stage == "full"` 이면 판정까지."""
    from supersub_agent.pose import extract_keypoints

    # 🔴 `observe=False` 다. 기본값 True 로 두면 데이터셋 수천 건이 서비스
    # 입력 관측에 섞여 들어가 그 통계가 못 쓰게 된다 (미결 12번과 같은 축).
    pose = extract_keypoints(video, observe=False)

    features = extract_features(
        pose.keypoints, pose.objects, rubric.impact_limb, rubric.impact_event, side
    )
    verify_rubric_coverage(rubric, features)

    out = {
        "clip": video.name,
        "frames": int(len(pose.keypoints)),
        # 프레임 번호만 남기지 않는다 (미결 7번 E-3).
        "timebase": {
            "source_fps": round(float(pose.source_fps), 4),
            "sampled_fps": round(float(pose.sampled_fps), 4),
            "target_fps": int(pose.target_fps),
            "seconds": frame_metrics_as_seconds(features, float(pose.sampled_fps)),
        },
        "features": features,
    }

    if stage == "full":
        from supersub_agent.judge import Judge
        from supersub_agent.scoring import aggregate

        judge = Judge(model_size="1.2B")
        judge.load()
        expected = [c.id for c in rubric.applicable_criteria(features)]
        out["result"] = aggregate(
            judge.judge_all(rubric, features), rubric, expected_ids=expected
        )
    return out


def run_batch(source, settings: config.Settings, cursor: config.Cursor,
              catalog: list, side: str) -> bool:
    """배치 하나. 남은 것이 없으면 False."""
    todo = [c for c in catalog if c.clip_id not in cursor.done][: settings.batch_size]
    if not todo:
        return False

    no = cursor.batch_no
    clips_dir = config.sport_dir(settings.sport, "clips", f"batch_{no:04d}")
    results_dir = config.sport_dir(settings.sport, "results")
    print(f"\n=== 배치 {no} · {len(todo)}건 · {clips_dir} ===")

    # --- 1단계: 받는다 ---------------------------------------------------
    #
    # 🔴 출처가 `prefetch` 를 갖고 있으면 그쪽을 쓴다. 단건으로 꺼내면 안 되는
    # 출처가 있다 — Picklebot 의 `.tar.xz` 는 랜덤 접근이 없어서 하나씩 꺼내면
    # 28GB 를 건수만큼 다시 푼다.
    got: list[tuple[object, Path]] = []
    if hasattr(source, "prefetch"):
        try:
            found = source.prefetch(todo, clips_dir)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"배치를 못 받았다: {type(exc).__name__}: {exc}") from exc
        got = [(c, found[c.clip_id]) for c in todo if c.clip_id in found]
        for c in todo:
            if c.clip_id not in found:
                print(f"  ✗ 아카이브에 없다: {c.clip_id}")
    else:
        for i, clip in enumerate(todo, 1):
            try:
                path = source.fetch(clip, clips_dir)
                got.append((clip, path))
            except Exception as exc:  # noqa: BLE001 — 한 건 실패가 배치를 막지 않는다
                print(f"  [{i}/{len(todo)}] ✗ 받기 실패 {clip.clip_id}: "
                      f"{type(exc).__name__}: {exc}")
    print(f"  받음 {len(got)}/{len(todo)}")
    if not got:
        raise SystemExit("한 건도 못 받았다. 자격증명·약관 동의를 확인할 것")

    # --- 2단계: 잰다 -----------------------------------------------------
    rubric = load_rubric(Path(settings.rubric))
    records, ok = [], 0
    t0 = time.time()
    for i, (clip, path) in enumerate(got, 1):
        try:
            rec = analyze_one(path, rubric, settings.stage, side)
            rec["label"] = clip.label
            records.append(rec)
            ok += 1
        except InsufficientQuality as exc:
            records.append({"clip": path.name, "label": clip.label,
                            "skipped": f"입력 품질 미달: {exc}"})
        except Exception as exc:  # noqa: BLE001
            records.append({"clip": path.name, "label": clip.label,
                            "error": f"{type(exc).__name__}: {exc}"})
        if i % 10 == 0 or i == len(got):
            print(f"  [{i}/{len(got)}] 분석 중 · 성공 {ok} · "
                  f"{time.time() - t0:.0f}초")

    report = results_dir / f"batch_{no:04d}.json"
    report.write_text(json.dumps({
        "sport": settings.sport,
        "batch_no": no,
        "rubric": settings.rubric,
        "stage": settings.stage,
        "swing_side": side,
        # 🔴 이 데이터에는 자세 정답이 없다. 결과를 인용할 사람이 이 줄을
        # 함께 보게 둔다 — 모듈 첫머리 경고와 같은 말이다.
        "caveat": "정답 없음 — 정확도가 아니라 측정이다. 39클립 평가셋과 섞지 말 것",
        "counted": {"fetched": len(got), "analyzed_ok": ok},
        "records": records,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  결과: {report}  (성공 {ok}/{len(got)})")

    # --- 3단계: 치운다 ---------------------------------------------------
    outcome = lifecycle.purge(
        [p for _, p in got], settings.storage_mode,
        s3_prefix=settings.s3_prefix, s3_region=settings.s3_region, batch_no=no,
    )
    print(f"  정리({settings.storage_mode}): {outcome.summary()}")
    # 빈 배치 폴더는 남겨 두지 않는다. 안에 뭐가 남았으면 그대로 둔다.
    if settings.storage_mode != "keep" and not any(clips_dir.iterdir()):
        clips_dir.rmdir()

    # --- 4단계: 커서 -----------------------------------------------------
    # 🔴 **받은 것만** 처리했다고 적는다. 받기에 실패한 것은 다음에 다시 시도한다.
    cursor.mark([c.clip_id for c, _ in got])
    return True


def main() -> None:
    ap = argparse.ArgumentParser(
        description="종목별 클립을 배치로 받아 재고 치우는 순환 파이프라인")
    ap.add_argument("--sport", required=True, choices=config.SPORTS)
    ap.add_argument("--rubric", required=True,
                    help="🔴 반드시 명시. 기본값에 기대면 종목이 어긋나도 조용히 채점된다")
    ap.add_argument("--storage-mode", default=config.DEFAULT_STORAGE_MODE,
                    choices=config.STORAGE_MODES,
                    help="배치를 다 쓴 뒤: keep(그대로) · delete(삭제) · s3(올린 뒤 삭제)")
    ap.add_argument("--s3-prefix", help="s3://버킷/접두사 — s3 모드에서 필수")
    ap.add_argument("--s3-region")
    ap.add_argument("--batch-size", type=int, default=config.BATCH_SIZE)
    ap.add_argument("--batches", type=int, default=0,
                    help="돌릴 배치 수. 0이면 다 소진할 때까지")
    ap.add_argument("--limit", type=int, default=0,
                    help="카탈로그를 앞에서 이만큼만 본다 (시험용)")
    ap.add_argument("--stage", default="pose", choices=("pose", "full"),
                    help="pose=지표까지 · full=판정(LLM)까지")
    ap.add_argument("--side", default="auto", choices=("auto", "left", "right"))
    ap.add_argument("--split", default=None, help="출처의 분할 (soccer/baseball)")
    ap.add_argument("--event", default=None, help="이벤트/라벨로 거른다")
    ap.add_argument("--local-dir", default=None,
                    help="이미 가진 폴더를 쓴다 (내려받지 않는다). 종목보다 우선한다")
    args = ap.parse_args()

    settings = config.Settings(
        sport=args.sport, batch_size=args.batch_size,
        storage_mode=args.storage_mode, s3_prefix=args.s3_prefix,
        s3_region=args.s3_region, rubric=args.rubric, stage=args.stage,
    )
    settings.validate()

    kw = {}
    if args.split:
        kw["split"] = args.split
    if args.event:
        kw["event" if args.sport == "soccer" else "label"] = args.event
    if args.local_dir:
        # 로컬 폴더에는 split·event 개념이 없다. 조용히 무시하지 않고 막는다.
        if kw:
            raise SystemExit("--local-dir 에는 --split/--event 를 함께 쓸 수 없다")
        source = sources.get_source(args.sport, local_dir=args.local_dir)
    else:
        source = sources.get_source(args.sport, **kw)

    print(f"저장 위치: {config.root()}  (명세의 {config.DEFAULT_ROOT})")
    print(f"출처: {type(source).__name__}")
    if getattr(source, "resolution_note", None):
        print(f"  ⚠️ 해상도: {source.resolution_note}")

    catalog = source.catalog()
    if args.limit:
        catalog = catalog[: args.limit]
    cursor = config.Cursor(args.sport)
    print(f"카탈로그 {len(catalog)}건 · 처리 완료 {len(cursor.done)}건 · "
          f"다음 배치 번호 {cursor.batch_no}")

    done_batches = 0
    while run_batch(source, settings, cursor, catalog, args.side):
        done_batches += 1
        if args.batches and done_batches >= args.batches:
            break
    print(f"\n배치 {done_batches}개 처리. 커서: {cursor.path}")


if __name__ == "__main__":
    main()
