"""영상의 한 시각에서 **고를 수 있는 사람들**을 낸다 (미결 `ho` 44번).

화면이 「이 사람으로 분석」을 띄우려면 분석을 걸기 **전에** 후보를 알아야 한다.

🔴 **분석 스크립트와 따로 둔 이유.** `analyze_s3.py` 에 모드를 하나 더 다는
길도 있었는데, 그러면 분석 경로에 분기가 생긴다 — 이 저장소는 「지정이 없을 때
결과가 **비트 동일**」을 기준으로 삼고 있어서(미결 18번) 그 경로에 손대는 것이
가장 비싸다. **검출만 하는 일은 검출만 하는 파일에 둔다.**

포즈 모델을 안 올린다. 사람 박스와 공은 **검출 결과만으로** 정해지므로
ViTPose 는 이 질문에 아무것도 보태지 않는다.

    # 로컬 파일
    uv run python scripts/detect_subjects.py clip.mp4 --at-ms 2000

    # S3 (워커가 부르는 형태)
    uv run python scripts/detect_subjects.py s3://버킷/videos/…/clip.mp4 \
        --at-ms 2000 --result-json /tmp/candidates.json

돌려주는 좌표는 **정규화 0~1** 이고, `people[].box` 를 그대로
`analyze_s3.py --subject-box` 로 넘길 수 있다. 🔴 **변환하지 말 것** — 그
자리가 곧 버그다(`tests/test_detect_candidates.py` 가 왕복을 검사한다).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent import storage  # noqa: E402
from supersub_agent.pose import DEFAULT_TARGET_FPS, detect_candidates  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", help="로컬 경로 또는 s3://버킷/키")
    ap.add_argument(
        "--at-ms", type=float, required=True,
        help="어느 시각의 화면에서 고르는가 (밀리초). 🔴 `--subject-at-ms` 와 "
             "같은 값을 주면 같은 프레임을 본다",
    )
    ap.add_argument("--fps", type=int, default=DEFAULT_TARGET_FPS)
    ap.add_argument("--region", default=None, help="S3 리전")
    ap.add_argument(
        "--result-json", default=None, metavar="PATH",
        help="결과를 이 파일에도 적는다. 🔴 **stdout 을 긁지 말 것** — 로그 "
             "문구가 바뀌면 깨진다 (`paik` 11번에서 배운 것)",
    )
    args = ap.parse_args()

    if args.at_ms < 0:
        raise SystemExit("--at-ms 는 0 이상이어야 한다")

    with tempfile.TemporaryDirectory() as tmp:
        if str(args.video).startswith("s3://"):
            local = Path(tmp) / Path(args.video).name
            storage.download(args.video, str(local), region=args.region)
        else:
            local = Path(args.video)
            if not local.is_file():
                raise SystemExit(f"영상을 찾을 수 없다: {local}")

        try:
            out = detect_candidates(local, args.at_ms, target_fps=args.fps)
        except ValueError as exc:
            # 🔴 읽을 프레임이 없는 것은 설정 오류가 아니라 **입력 문제**다.
            #    분석 쪽 품질 게이트(2)와 같은 코드를 써서 「사람이 손봐야
            #    풀린다」는 뜻을 맞춘다.
            print(f"\n후보를 낼 수 없다: {exc}")
            raise SystemExit(2) from exc

    out["source_video"] = str(args.video)
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.result_json:
        Path(args.result_json).write_text(text + "\n", encoding="utf-8")
    print(text)

    n = len(out["people"])
    ball = "있음" if out["ball"] else "없음"
    # 🔴 사람이 0명이어도 **실패가 아니다.** 검출이 놓칠 수 있고, 그때 화면은
    #    지금처럼 드래그로 떨어지면 된다 (`ho` 44번). 실패로 만들면 화면이
    #    「사람이 없습니다」로 막아 버린다.
    print(f"\n[후보] {n}명 · 공 {ball} · 프레임 {out['frame']}"
          f"{' (창 밖이라 끝으로 당겼다)' if out['at_clamped'] else ''}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
