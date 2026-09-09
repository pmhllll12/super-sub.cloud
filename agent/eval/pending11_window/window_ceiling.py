#!/usr/bin/env python3
"""분석 창(`DEFAULT_MAX_SECONDS`)을 얼마나 넓힐 수 있는가 (미결 `jin` 11번).

    uv run python eval/pending11_window/window_ceiling.py

**왜 다시 재는가.** 2026.09.07 회신에서 「창을 60초로 넓히는 길은 없다」고
적었는데, 그때 근거는 **추정**이었다(1080p 1,800장 ≈ 11GB). 그 뒤 `ho` 9번에서
RSS 를 실측하고 가드를 바이트 예산으로 옮겼다. **추정이 실측으로 바뀌었으므로
결론이 아직 서는지 다시 본다** — 결론은 그대로였지만 **1080p 여유가 10초가
아니라 40초라는 것**은 그때 알 수 없었다.

세 가지를 낸다.

1. **예산이 허락하는 창** — 해상도별로 `DEFAULT_MAX_FRAME_BYTES` 안에 드는 초
2. **인스턴스가 허락하는 절대 상한** — 예산을 늘린다고 가정했을 때의 천장.
   60초가 닿는지를 여기서 판정한다
3. **B-6 안전선** — 창을 넓혀도 평가셋 39클립의 장수가 안 변하는 최대값.
   여기를 넘으면 `features` 가 달라져 **B-6 재실행을 부른다**

조사 스크립트라 `src/`를 고치지 않는다 — 상수와 규칙을 production 과
`pending9_budget` 에서 import 한다. 리터럴을 복제하면 값이 바뀔 때 이 측정이
조용히 낡는다(미결 10번의 형태).
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "pending9_budget"))

from supersub_agent.pose import (  # noqa: E402
    DEFAULT_MAX_FRAME_BYTES,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MAX_SECONDS,
    DEFAULT_TARGET_FPS,
    frames_within_budget,
)
from verify_budget import BASE_MB, INSTANCE_MB, MB, VLLM_MB  # noqa: E402

SPECS = Path("/mnt/d/supersub-phaseA/clip_specs.csv")

# 요청이 정한 업로드 상한(SFR-001, `fastapi/.../video_rules.py` 의
# `MAX_DURATION_MS`). 🔴 남의 영역 값이라 여기서 **읽기만** 한다.
UPLOAD_LIMIT_SECONDS = 60.0

RESOLUTIONS = [
    ("4K 세로", 2160, 3840),
    ("4K 가로", 3840, 2160),
    ("1440p", 2560, 1440),
    ("1080p", 1920, 1080),
    ("720p", 1280, 720),
]


def sampled_fps(src_fps: float) -> float:
    """`pose.read_frames_ex` 의 샘플링 규칙. 바꾸려면 그쪽을 바꾸고 여기를 맞춘다."""
    step = max(1, round(src_fps / DEFAULT_TARGET_FPS))
    return src_fps / step


def frames_used(src_fps: float, avail_frames: int, guard: int,
                window_s: float) -> int:
    """이 클립에서 실제로 쓰이는 장수. 창·가드·클립 길이 중 먼저 걸리는 쪽이 이긴다."""
    s = sampled_fps(src_fps)
    want = max(1, math.ceil(window_s * s))
    step = max(1, round(src_fps / DEFAULT_TARGET_FPS))
    available = max(1, math.ceil(avail_frames / step))
    return min(want, guard, available)


def budget_windows() -> None:
    print(f"[1] 예산이 허락하는 창 — 예산 {DEFAULT_MAX_FRAME_BYTES / MB:,.0f}MB "
          f"(= 4K 세로 300장) · target {DEFAULT_TARGET_FPS}fps")
    print(f"    지금 창은 {DEFAULT_MAX_SECONDS}초다.\n")
    print(f"    {'해상도':<10}{'예산 장수':>10}{'창 상한':>10}   여유")
    for label, w, h in RESOLUTIONS:
        n = frames_within_budget(w, h)
        secs = n / DEFAULT_TARGET_FPS
        slack = ("**없다 — 지금 창이 곧 상한**" if secs <= DEFAULT_MAX_SECONDS
                 else f"{secs / DEFAULT_MAX_SECONDS:.0f}배")
        print(f"    {label:<10}{n:>10,}{secs:>9.1f}초   {slack}")
    print("\n    🔴 4K 는 지금 창이 곧 상한이다. 넓히면 **4K 만 못 따라온다.**")


def instance_ceiling() -> None:
    print(f"\n[2] 인스턴스가 허락하는 절대 상한 — 예산을 늘린다고 가정했을 때")
    room = INSTANCE_MB * 0.90 - BASE_MB - VLLM_MB
    print(f"    한도 {INSTANCE_MB * 0.90:,.0f}MB (인스턴스 {INSTANCE_MB:,}의 90%)"
          f" - base {BASE_MB:,} - vLLM {VLLM_MB:,} = **프레임 몫 {room:,.0f}MB**\n")
    print(f"    {'해상도':<10}{'천장 장수':>10}{'= 창':>9}   60초 업로드를")
    reaches, misses = [], []
    for label, w, h in RESOLUTIONS:
        per_frame_mb = w * h * 3 / MB
        n = int(room / per_frame_mb)
        secs = n / DEFAULT_TARGET_FPS
        hit = secs >= UPLOAD_LIMIT_SECONDS
        (reaches if hit else misses).append(label)
        verdict = ("**닿는다**" if hit
                   else f"못 닿는다 ({secs / UPLOAD_LIMIT_SECONDS:.0%})")
        print(f"    {label:<10}{n:>10,}{secs:>8.1f}초   {verdict}")

    # 🔴 판정을 문장으로 박지 않는다. 표와 어긋난 단언을 한 번 찍었고
    #    (720p 는 닿는데 「어느 해상도도 못 닿는다」고 적었다) 표를 안 읽으면
    #    그대로 믿게 된다. 결론은 위 계산에서 끌어낸다.
    lim = f"{UPLOAD_LIMIT_SECONDS:.0f}초"
    if not reaches:
        print(f"\n    🔴 **어느 해상도도 {lim}에 못 닿는다** — 예산을 인스턴스"
              " 천장까지 올려도 그렇다.")
    else:
        print(f"\n    🔴 **{lim}는 해상도를 낮춰야만 닿는다**:"
              f" {', '.join(reaches)} 는 닿고, {', '.join(misses)} 는 못 닿는다.")
        print(f"    → {lim}를 **모든 입력에 보장할 수는 없다.** 낮은 해상도로만"
              " 닿는 것은 화질을 깎아 창을 사는 것이고,")
        print("      그것이 포즈 정확도에 미치는 영향은 **재보지 않았다** —"
              " 재기 전에는 선택지로 세지 않는다.")


def b6_safe_window() -> None:
    print(f"\n[3] B-6 안전선 — 창을 넓혀도 평가셋 장수가 안 변하는 최대값")
    if not SPECS.exists():
        print(f"    평가셋 명세가 없어 건너뛴다: {SPECS}")
        print("    🔴 이 값 없이는 창을 옮기지 말 것 — B-6 재실행 여부를 모른다.")
        return

    rows = list(csv.DictReader(SPECS.open()))
    base = []
    for r in rows:
        w, h = int(r["w"]), int(r["h"])
        guard = frames_within_budget(w, h)
        n0 = frames_used(float(r["fps"]), int(r["nframes"]), guard,
                         DEFAULT_MAX_SECONDS)
        base.append((r["clip_id"], float(r["fps"]), int(r["nframes"]), guard, n0))

    # 창을 0.5초씩 넓히며 처음으로 장수가 달라지는 지점을 찾는다.
    changed_at: float | None = None
    window = DEFAULT_MAX_SECONDS
    while window <= UPLOAD_LIMIT_SECONDS:
        window = round(window + 0.5, 1)
        movers = [cid for cid, f, nf, g, n0 in base
                  if frames_used(f, nf, g, window) != n0]
        if movers:
            changed_at = window
            break

    print(f"    평가셋 {len(rows)}클립 · 지금 창 {DEFAULT_MAX_SECONDS}초")
    if changed_at is None:
        print(f"    ✅ **{UPLOAD_LIMIT_SECONDS:.0f}초까지 한 클립도 안 변한다.**")
        print("    전부 창보다 짧아서 창이 구속하지 않는다 —"
              " **창을 넓혀도 B-6 재실행을 부르지 않는다.**")
    else:
        print(f"    🔴 창을 **{changed_at}초**로 넓히면 장수가 달라지는 클립이 있다:")
        for cid, f, nf, g, n0 in base:
            n1 = frames_used(f, nf, g, changed_at)
            if n1 != n0:
                print(f"      {cid} {f}fps {nf}프레임 → {n0}장에서 {n1}장")
        print(f"    **안전선은 {round(changed_at - 0.5, 1)}초다.** 넘으면"
              " `features` 가 달라져 B-6 재실행을 부른다.")

    binding = [(cid, n0, g) for cid, f, nf, g, n0 in base if n0 == g]
    print(f"\n    참고 · 지금 가드가 구속하는 클립: {len(binding)}건"
          + (f" {binding[:5]}" if binding else " (없다)"))


def main() -> None:
    print(__doc__.split("\n")[0] + "\n")
    budget_windows()
    instance_ceiling()
    b6_safe_window()
    print(f"\n(폴백 상수 `DEFAULT_MAX_FRAMES`={DEFAULT_MAX_FRAMES} 는 해상도를"
          " 모르는 컨테이너에서만 쓴다.)")


if __name__ == "__main__":
    main()
