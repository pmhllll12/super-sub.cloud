#!/usr/bin/env python3
"""**찍은 사람이 실제로 분석됐는가** — 같은 클립을 자동/지정 두 번 돌려 비교한다.

    uv run python eval/subject_pick/verify_pick.py <영상> \
        --box 0.492,0.287,0.083,0.306 --at-ms 3000

## 왜 판정까지 안 돌리나

묻는 것이 "누구를 봤는가"뿐이라 루브릭도 판정 모델도 필요 없다. 품질 게이트도
`extract_features` 안에 있어 여기서는 걸리지 않는다 — **대상이 틀린 클립도
끝까지 돌려서 무엇이 골라졌는지 봐야 한다.** 게이트에 막혀 못 보면 그것이
이 확인이 막으려던 상황이다.

## 무엇으로 확인하는가

정답은 **사람이 그린 박스 하나**다. 그래서 두 가지만 말한다.

  1. 자동과 지정이 **갈리는가** — 갈리지 않으면 지정이 아무 일도 안 한 것이다
  2. 지정 프레임에서 고른 박스가 **찍은 박스와 얼마나 겹치는가**(IoU)

🔴 **"옳은 사람을 골랐는가"는 여전히 말하지 않는다.** 찍은 박스가 정답이라는
보장은 사람이 그것을 그렸다는 것뿐이다(미결 18번의 「라벨 수집」 절).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.pose import (  # noqa: E402
    _iou,
    extract_keypoints,
    parse_subject_spec,
    subject_envelope,
)


def run(video: Path, subject, fps: int) -> dict:
    # observe=False — 확인 실행은 서비스 입력이 아니다.
    result = extract_keypoints(video, target_fps=fps, observe=False, subject=subject)
    env = subject_envelope(result, int(len(result.keypoints)))
    env["_boxes_px"] = result.subject_boxes
    return env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--box", required=True, metavar="x,y,w,h",
                    help="사람이 찍은 **정규화 0~1** 박스")
    ap.add_argument("--at-ms", type=float, required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    subject = parse_subject_spec(args.box, args.at_ms)
    assert subject is not None

    print(f"[1/2] 자동 — 지금까지의 동작")
    auto = run(args.video, None, args.fps)
    print(f"[2/2] 지정 — {args.box} @ {args.at_ms:.0f}ms")
    picked = run(args.video, subject, args.fps)

    n = auto["frames"]
    differing = sum(
        1 for a, b in zip(auto["_boxes_px"], picked["_boxes_px"]) if a != b
    )
    anchor = picked.get("anchor_frame")

    print("\n" + "=" * 62)
    print(f"프레임 {n} · 자동이 고른 프레임 {auto['frames_with_box']} · "
          f"지정이 고른 프레임 {picked['frames_with_box']}")
    print(f"선택이 갈린 프레임: {differing}/{n} ({differing / n:.0%})")
    print(f"지정 결과: {picked['source']}"
          + (f" — {picked['why']}" if picked["why"] else ""))
    if anchor is not None:
        print(f"닻 {anchor}프레임 · 찍은 박스와의 IoU {picked['anchor_iou']}"
              f" · 격자 어긋남 {picked['grid_offset_frames']}프레임"
              f" · 창 밖 당김 {picked['at_clamped']}")
        print(f"연속성 끊김 {picked['continuity_breaks']}회")
        a, p = auto["_boxes_px"][anchor], picked["_boxes_px"][anchor]
        print(f"  자동이 고른 박스 {a}")
        print(f"  지정이 고른 박스 {p}")
        if a and p:
            print(f"  둘 사이 IoU {_iou(a, p):.3f}  "
                  "(0에 가까우면 아예 다른 사람이다)")

    if differing == 0:
        print("\n🔴 갈리지 않았다 — 지정이 아무 일도 하지 않았다.")

    if args.out:
        for env in (auto, picked):
            env.pop("_boxes_px", None)
        args.out.write_text(
            json.dumps({"video": str(args.video), "specified_box": args.box,
                        "at_ms": args.at_ms, "auto": auto, "picked": picked,
                        "differing_frames": differing},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
