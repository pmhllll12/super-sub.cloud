"""SoccerNet 방송 클립을 관문용으로 몇 편 받는다 (미결 `ho` 46번).

🔴 **수집 파이프라인을 대체하지 않는다.** 출처·인증·안전한 이름은 전부
`scripts/dataset_pipeline/sources.py` 의 `SoccerNet10s` 를 그대로 쓴다 —
여기 있는 것은 **「관문에 댈 만큼만 받는다」**는 얇은 껍데기다.
🔴 기존 `clips/batch_0000` 과 수집 커서(`_state.json`)를 **안 건드린다**
(별도 뿌리 `paths.soccernet_clips_root()`).

인증이 필요하다 — `hf auth login` (미결 46번에 절차를 적어 두었다).

    cd agent && uv run python eval/sample_gate/fetch_soccernet.py --n 40
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))

from scripts.dataset_pipeline import sources  # noqa: E402

import paths  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=40, help="받을 편수")
    ap.add_argument("--event", default="Shots",
                    help="SoccerNet 라벨 (Shots·Goal·Foul·Throw-in·Ball out of play)")
    ap.add_argument("--split", default="train")
    args = ap.parse_args()

    dest = paths.soccernet_clips_root()
    dest.mkdir(parents=True, exist_ok=True)

    src = sources.SoccerNet10s(split=args.split, event=args.event)
    cat = src.catalog()
    print(f"{args.event} {len(cat)}건 중 앞에서 {args.n}편 → {dest}\n")

    # 🔴 **앞에서부터** 고른다. 무작위로 고르면 회차마다 표본이 달라져
    #    「같은 표본에서 다시 쟀다」를 말할 수 없다. `catalog()` 는 정렬돼 있다.
    got = 0
    for clip in cat[: args.n]:
        try:
            p = src.fetch(clip, dest)
        except Exception as exc:  # noqa: BLE001 — 한 편이 죽어도 나머지는 받는다
            print(f"  🔴 {clip.clip_id[:50]:50s} {type(exc).__name__}")
            continue
        got += 1
        print(f"  [{got}/{args.n}] {p.name[:60]:60s} {p.stat().st_size/1e6:5.2f}MB")

    print(f"\n{got}편. 다음:")
    print("  uv run python eval/sample_gate/sample_gate.py --sample soccernet")


if __name__ == "__main__":
    main()
