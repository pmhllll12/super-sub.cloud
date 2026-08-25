"""영상 → 측정값. 판정 모델을 적재하지 않는다.

    uv run python scripts/measure.py data/shot01.mp4 --limb arm

루브릭을 새로 쓸 때 쓰는 스크립트다. 임계값(bands)을 정하려면 이 파이프라인이
그 종목의 영상에서 **실제로 어떤 값을 내는지** 먼저 봐야 한다. analyze.py는
판정 모델을 올리느라 한 번에 20초 이상 걸리는데, 루브릭 초안 단계에서는 등급
문장이 아니라 수치만 필요하다.

--limb은 임팩트를 정의할 사지다(루브릭의 kinematics.impact_limb과 같은 값).
축구 슈팅은 leg, 농구 슛·배구 스파이크·테니스 서브는 arm이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent.features import (  # noqa: E402
    InsufficientQuality,
    check_quality,
    extract_features,
)
from supersub_agent.pose import extract_keypoints  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--limb", default="leg", choices=["leg", "arm"])
    ap.add_argument(
        "--event", default="extension_peak",
        choices=["extension_peak", "distal_apex"],
        help="임팩트로 삼을 사건 (루브릭의 kinematics.impact_event와 같은 값)",
    )
    ap.add_argument("--fps", type=int, default=15)
    args = ap.parse_args()

    pose = extract_keypoints(args.video, target_fps=args.fps)
    print(f"[포즈] {len(pose.keypoints)}프레임 · 원본 {pose.source_fps:.1f}fps "
          f"· 실효 {pose.sampled_fps:.2f}fps")

    # 사지별 유효 프레임 비율 — 어느 쪽 임계로 갈지 판단하는 근거다.
    for limb in ("leg", "arm"):
        try:
            ratio = check_quality(pose.keypoints, limb=limb)
            print(f"  {limb:<4} 유효 프레임 {ratio:.0%}")
        except InsufficientQuality as exc:
            print(f"  {limb:<4} 품질 미달 — {exc}")

    for name, track in pose.objects.items():
        print(f"  도구 {name} 검출률 {pose.object_detection_ratio(name):.0%}")

    try:
        features = extract_features(
            pose.keypoints, pose.objects, args.limb, args.event
        )
    except InsufficientQuality as exc:
        print(f"\n측정 불가: {exc}")
        raise SystemExit(2) from exc

    print(f"\n[측정] impact_limb={args.limb} impact_event={args.event} "
          f"· 임팩트 {features['impact_frame']}프레임 "
          f"({pose.frame_to_seconds(int(features['impact_frame'])):.2f}초)")
    print(json.dumps(features, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
