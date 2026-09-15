"""이분 탐색의 good/bad 판정 (미결 `ho` 47번).

축구 19클립 × 5 selector = **95행**을 2026-09-08 판과 **전 열** 대조한다.
🔴 야구·농구 3클립은 **뺀다** — 39번 종목 정리로 사라진 것이 이미 설명된다.

    uv run python eval/pending47_baseline_audit/verdict.py <재실행 csv>
    # 종료코드 0 = good(일치) · 1 = bad(다름)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline_2026-09-08_track2.csv"
KEY = ("clip_id", "comparison_selector")
#: 루브릭이 지워져 사라진 클립 — 갈림과 무관하다(미결 39번).
DROPPED = {"baseball_pitch_trim.mp4", "bball_shot.mp4", "bball_layup_trim.mp4"}


def load(path: Path) -> dict[tuple, dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return {tuple(r[k] for k in KEY): r
                for r in csv.DictReader(fh) if r["clip_id"] not in DROPPED}


def main() -> int:
    now = load(Path(sys.argv[1]))
    was = load(BASELINE)
    only = (set(was) ^ set(now))
    if only:
        print(f"🔴 키가 다르다 ({len(only)}개): {sorted(only)[:5]}")
        return 1

    cols = [c for c in next(iter(was.values())) if c in next(iter(now.values()))]
    bad = []
    for k in sorted(was):
        for c in cols:
            if was[k][c] != now[k][c]:
                bad.append(f"{'|'.join(k)}.{c}: {was[k][c]!r} → {now[k][c]!r}")

    print(f"{len(was)}행 × {len(cols)}열 대조 — 불일치 **{len(bad)}**")
    for x in bad[:8]:
        print("  " + x)
    print("good (일치)" if not bad else "bad (다름)")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
