#!/usr/bin/env python3
"""메모리 가드가 **분석 창을 얼마나 줄이는가** (미결 ho 9번 · 로드맵 E-3 인접 결함).

    uv run python eval/pending9_window/coverage.py

🔴 **이 스크립트는 고쳐지기 전의 크기를 재는 자리다** (2026-09-08 이후).
가드는 이제 장수가 아니라 **바이트 예산**이고(`DEFAULT_MAX_FRAME_BYTES`),
아래 `DEFAULT_MAX_FRAMES`는 해상도를 모르는 컨테이너에서만 쓰는 폴백이다.
**고친 뒤의 판정은 `eval/pending9_budget/verify_budget.py`가 한다** — 이쪽은
「무엇이 문제였나」를 남기려고 그대로 둔다. 지우면 왜 고쳤는지가 사라진다.

창은 `DEFAULT_MAX_SECONDS`(초)이고 옛 가드는 `DEFAULT_MAX_FRAMES`(장)였다. 둘 중
먼저 걸리는 쪽이 이긴다 — 그래서 **실효 fps가 높은 소스에서는 가드가 이기고,
보기로 한 10초를 못 봤다.** 이 스크립트는 그 구간과 최악값을 낸다.

조사 스크립트라 `src/`를 고치지 않는다 — 상수와 규칙을 production에서 import한다.
리터럴을 복제하면 값이 바뀔 때 이 측정이 조용히 낡는다(미결 10번의 형태).
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.pose import (  # noqa: E402
    DEFAULT_MAX_FRAME_BYTES,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    frames_within_budget,
)

SPECS = Path("/mnt/d/supersub-phaseA/clip_specs.csv")


def coverage(src_fps: float) -> tuple[float, int, str]:
    """이 소스 fps에서 실제로 덮는 초, 장수, 무엇이 이겼는지.

    `pose.read_frames_ex`와 같은 규칙이다 — 바꾸려면 그쪽을 바꾸고 여기를 맞춘다.
    """
    step = max(1, round(src_fps / DEFAULT_TARGET_FPS))
    sampled = src_fps / step
    want = max(1, math.ceil(DEFAULT_MAX_SECONDS * sampled))
    limit = min(DEFAULT_MAX_FRAMES, want)
    return limit / sampled, limit, ("memory_guard" if limit < want else "window")


def main() -> None:
    print(f"창 {DEFAULT_MAX_SECONDS}초 · 가드 {DEFAULT_MAX_FRAMES}장 · "
          f"목표 {DEFAULT_TARGET_FPS}fps\n")

    short: list[tuple[float, float]] = []
    fps = 1.0
    while fps <= 240.0:
        cov, _, who = coverage(fps)
        if who == "memory_guard":
            short.append((fps, cov))
        fps = round(fps + 0.5, 1)

    if not short:
        print("가드가 창을 줄이는 소스 fps가 없다.")
    else:
        worst = min(short, key=lambda r: r[1])
        lo, hi = short[0][0], short[-1][0]
        print(f"가드가 이기는 소스 fps: {len(short)}개 지점 ({lo}~{hi}fps 사이)")
        print(f"  최악: {worst[0]}fps → {worst[1]:.2f}초 "
              f"(보기로 한 {DEFAULT_MAX_SECONDS}초의 {worst[1] / DEFAULT_MAX_SECONDS:.0%})")
        print("  step이 1이라 원본 fps가 그대로 넘어오는 30.5~44.5fps 구간이 가장 나쁘다.\n")

    if not SPECS.exists():
        print(f"평가셋 명세가 없어 대조를 건너뛴다: {SPECS}")
        return

    rows = list(csv.DictReader(SPECS.open()))
    hit = [(r["clip_id"], float(r["fps"]), coverage(float(r["fps"]))[0])
           for r in rows if coverage(float(r["fps"]))[2] == "memory_guard"]
    print(f"평가셋 {len(rows)}클립 중 창이 줄어드는 것: {len(hit)}건")
    for cid, f, cov in hit:
        print(f"  {cid} {f}fps → {cov:.2f}초")
    if not hit:
        print("  🔴 **B-6 재실행을 부르지 않는다** — 가드를 고쳐도 이 39클립의 "
              "결과는 한 비트도 달라지지 않는다.")


# ─────────────────────────────────────────────────────────────────────────────
# ✅ **처방은 들어갔다 (2026-09-08).** 가드가 바이트 예산이 됐다.
#
# 아래는 그때 계산했던 처방 후보이고, production 상수를 import 하므로 지금은
# **실제로 들어간 값**을 찍는다. 판정(기준 A~E)은 여기가 아니라
# `eval/pending9_budget/verify_budget.py`가 한다.


def report_budget() -> None:
    print(f"\n[처방 — 들어갔다] 예산 {DEFAULT_MAX_FRAME_BYTES / 1e6:,.0f}MB "
          f"(= 4K 세로 300장)")
    for label, (w, h) in (("4K 세로", (2160, 3840)), ("1080p", (1920, 1080)),
                          ("720p", (1280, 720))):
        n = frames_within_budget(w, h)
        need = math.ceil(DEFAULT_MAX_SECONDS * 44.5)  # 최악 fps에서 창을 지킬 장수
        ok = "창을 지킨다" if n >= need else "여전히 못 지킨다"
        print(f"  {label:8} {n:5d}장  (44.5fps 창에 필요한 {need}장 대비 → {ok})")
    print("  🔴 4K는 300장 그대로다 — 지금 동작을 바꾸지 않으면서 나머지를 풀었다.")
    print("  RSS 실측은 끝났다: 4K 300장 9,061MB (eval/pending9_rss/RESULTS.md).")


if __name__ == "__main__":
    main()
    report_budget()
