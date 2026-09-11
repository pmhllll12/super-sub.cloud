#!/usr/bin/env python3
"""바이트 예산 가드의 합격 판정 (미결 ho 9번).

    uv run python eval/pending9_budget/verify_budget.py

기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md)에 **구현 전에** 고정했다.
여기서 고치지 않는다 — 결과를 보고 합격선을 옮기면 그 순간 근거가 아니게 된다.

조사 스크립트라 `src/`를 고치지 않는다. 규칙과 상수를 production에서
**import만** 한다 — 리터럴을 복제하면 값이 바뀔 때 이 판정이 조용히 낡는다
(미결 10번의 형태).
"""
from __future__ import annotations

import csv
import inspect
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent import pose  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    DEFAULT_MAX_FRAME_BYTES,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    frames_within_budget,
)


# 🔴 경로를 박지 않는다 — `eval/phaseA/paths.py` 가 정한다 (미결 14번).
#    박아 두면 다른 기계에서 안 돌고, 저장소 사본을 떠도 읽히지 않는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phaseA"))
from paths import external_root  # noqa: E402

SPECS = external_root() / "clip_specs.csv"

# 🔴 **10진 MB 다 (1e6). MiB 가 아니다.** `pending9_rss` 의 실측표가 10진이라
# (1920×1080×3×60 = 373,248,000B 를 「373MB」로 적었다) 여기서 MiB 로 재면
# 같은 예산이 7,465 와 7,119 두 값으로 보인다. **메모리 예산에서 단위를 섞으면
# 판정이 조용히 어긋난다** — 처음 쓸 때 실제로 섞여 있었다.
MB = 1_000_000

# 사전 등록 2절의 실측값 (EC2 g4dn.xlarge · eval/pending9_rss/RESULTS.md).
# 위와 같은 10진 MB 다.
INSTANCE_MB = 16_162
VLLM_MB = 3_200
BASE_MB = 1_748

# 기준 C 가 훑는 구간. step 이 1이라 원본 fps 가 그대로 넘어오는 자리다.
GUARD_BAND = (30.5, 44.5)


def limit_for(src_fps: float, max_frames: int) -> tuple[int, str]:
    """이 가드에서 실제로 읽는 장수와 무엇이 이겼는지.

    `pose.read_frames_ex` 와 같은 규칙이다 — 바꾸려면 그쪽을 바꾸고 여기를 맞춘다.
    """
    step = max(1, round(src_fps / DEFAULT_TARGET_FPS))
    sampled = src_fps / step
    want = max(1, math.ceil(DEFAULT_MAX_SECONDS * sampled))
    limit = min(max_frames, want)
    return limit, ("memory_guard" if limit < want else "window")


def criterion_a() -> tuple[bool, str]:
    """평가셋 39클립의 분석 장수가 불변인가. 1건이라도 다르면 불합격."""
    if not SPECS.exists():
        return False, f"판정 불가 — 평가셋 명세가 없다: {SPECS}"

    rows = list(csv.DictReader(SPECS.open()))
    moved = []
    for r in rows:
        fps, w, h = float(r["fps"]), int(r["w"]), int(r["h"])
        old, _ = limit_for(fps, DEFAULT_MAX_FRAMES)
        new, _ = limit_for(fps, frames_within_budget(w, h))
        if old != new:
            moved.append((r["clip_id"], w, h, fps, old, new))

    if moved:
        lines = "\n".join(
            f"      {c} {w}×{h} {f}fps: {o}장 → {n}장" for c, w, h, f, o, n in moved
        )
        return False, f"{len(moved)}/{len(rows)}건이 바뀐다 — B-6 재실행을 부른다\n{lines}"
    return True, f"{len(rows)}/{len(rows)}건 불변 — B-6 재실행을 부르지 않는다"


def criterion_b() -> tuple[bool, str]:
    """4K 세로 상한이 정확히 300장인가."""
    n = frames_within_budget(2160, 3840)
    return n == 300, f"2160×3840 → {n}장 (요구 300장)"


def criterion_c() -> tuple[bool, str]:
    """1080p·30.5~44.5fps 전 지점에서 가드가 창을 먹지 않는가."""
    cap = frames_within_budget(1920, 1080)
    hit = []
    fps = GUARD_BAND[0]
    while fps <= GUARD_BAND[1]:
        if limit_for(fps, cap)[1] == "memory_guard":
            hit.append(fps)
        fps = round(fps + 0.5, 1)
    lo, hi = GUARD_BAND
    return not hit, (
        f"1080p 상한 {cap}장 · {lo}~{hi}fps 구간 memory_guard {len(hit)}건"
        + (f" {hit[:5]}" if hit else "")
    )


def criterion_d() -> tuple[bool, str]:
    """동거 몫을 뺀 뒤에도 예산이 인스턴스 RAM의 90% 안인가."""
    used = DEFAULT_MAX_FRAME_BYTES / MB + BASE_MB + VLLM_MB
    ceiling = INSTANCE_MB * 0.90
    return used <= ceiling, (
        f"예산 {DEFAULT_MAX_FRAME_BYTES / MB:,.0f} + base {BASE_MB:,} + "
        f"vLLM {VLLM_MB:,} = {used:,.0f}MB / 한도 {ceiling:,.0f}MB "
        f"(인스턴스 {INSTANCE_MB:,}MB의 90%)"
    )


def criterion_e() -> tuple[bool, str]:
    """예산이 런타임 상태에 의존하지 않는가.

    같은 입력이 같은 장수를 내는지와, 예산 경로에 **메모리·환경 조회가 없는지**
    를 함께 본다. 값만 보면 「이번에는 같았다」밖에 못 말한다.
    """
    repeated = {frames_within_budget(1920, 1080) for _ in range(50)}
    stable = len(repeated) == 1

    src = inspect.getsource(frames_within_budget)
    probes = re.findall(
        r"meminfo|MemAvailable|virtual_memory|psutil|os\.environ|getenv|sysconf", src
    )
    return stable and not probes, (
        f"50회 반복 결과 {repeated} · 예산 경로의 런타임 조회 {len(probes)}곳"
    )


CRITERIA = [
    ("A", "평가셋 39클립 장수 불변", criterion_a),
    ("B", "4K 세로 상한 300장 그대로", criterion_b),
    ("C", "30.5~44.5fps 에서 가드가 창을 안 먹는다", criterion_c),
    ("D", "동거 몫을 뺀 예산이 인스턴스 안", criterion_d),
    ("E", "예산이 런타임 상태에 의존하지 않는다", criterion_e),
]


def main() -> int:
    print(f"예산 {DEFAULT_MAX_FRAME_BYTES / MB:,.0f}MB · 창 {DEFAULT_MAX_SECONDS}초 · "
          f"목표 {DEFAULT_TARGET_FPS}fps · 폴백 {DEFAULT_MAX_FRAMES}장\n")

    failed = 0
    for tag, what, fn in CRITERIA:
        ok, detail = fn()
        failed += not ok
        print(f"  [{'✅' if ok else '🔴'}] {tag}. {what}\n      {detail}")

    print("\n해상도별 상한 (예산 안 장수):")
    for label, (w, h) in (("4K 세로", (2160, 3840)), ("1080p", (1920, 1080)),
                          ("720p", (1280, 720)), ("480p", (640, 480))):
        n = frames_within_budget(w, h)
        need = math.ceil(DEFAULT_MAX_SECONDS * GUARD_BAND[1])
        print(f"  {label:8} {n:6,d}장  ({GUARD_BAND[1]}fps 창에 필요한 {need}장 → "
              f"{'지킨다' if n >= need else '못 지킨다'})")

    print(f"\n판정: {len(CRITERIA) - failed}/{len(CRITERIA)} 합격")
    # 🔴 불합격이면 종료 코드로 말한다. 로그만 남기면 CI 도 사람도 안 읽는다.
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
