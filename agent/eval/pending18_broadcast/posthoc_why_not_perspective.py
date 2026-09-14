"""사후 관찰 — **원근이 아니면 무엇인가** (미결 `ho` 18번 12회차).

🔴 **판정에 안 쓴다.** 사전 등록 판정(판별불가 — G 불통과)은 이미 났다.
이것은 **다음 회차의 방향**을 정하기 위한 관측이다. 🔴 결과를 보고 12회차의
기준을 고치지 않는다.

물음: `M` 이 17.7% 인데 **고른 사람이 최근접 후보보다 크지 않다**(높이비 중앙
1.19). 그러면 `_largest_person_box` 는 **왜** 딴 사람을 고르는가.

가설 셋 — 셋 다 **면적**이 필요한데 본 회차 행에는 높이만 남아 있어서
검출을 다시 돈다(주 층에 든 **9편만**, GPU 약 3분).

| | 가설 | 재는 것 |
|---|---|---|
| **(a)** | **거의 동률이다** — 비슷한 크기가 여럿이라 `argmax` 가 사실상 임의다 | 최대 면적 대비 **10% 안**에 든 후보 수 |
| **(b)** | **넓은 박스가 이긴다** — 뭉친 사람들을 한 박스로 잡아 면적만 크다 | 고른 박스의 **가로세로비** 대 최근접 후보 |
| **(c)** | 높이는 비슷한데 **면적은 크다** | 면적비 대 높이비 |

    cd agent && uv run python eval/pending18_broadcast/posthoc_why_not_perspective.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_ball_proximity"))

from measure_proximity import NEAR, detect_clip, foot_point, gate_by_speed  # noqa: E402
from supersub_agent.pose import _load_detector  # noqa: E402

import paths  # noqa: E402

HERE = Path(__file__).resolve().parent
TIE = 0.10   # 최대 면적의 몇 % 안이면 「사실상 동률」로 볼 것인가


def main() -> None:
    import torch

    raw = json.loads((HERE / "broadcast_raw.json").read_text(encoding="utf-8"))
    wanted = {r["clip"] for r in raw if r.get("n_near", 0) >= 5}
    clips = [p for p in sorted(paths.soccernet_clips_root().glob("*.mp4"))
             if p.name in wanted]
    print(f"주 층에 든 {len(clips)}편만 다시 돈다 (검출만)\n")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    det_pair = _load_detector(device)

    tie_counts, aspect_chosen, aspect_argmin = [], [], []
    area_ratio, height_ratio, cand_counts = [], [], []
    chosen_is_widest = 0
    rows_seen = 0

    for clip in clips:
        det = detect_clip(clip, det_pair, device)
        cands, ball_t = det["cands"], det["objects"].get("sports_ball")
        if ball_t is None:
            continue
        heights = [b[3] for f in cands for b in f]
        H = float(statistics.median(heights)) if heights else 0.0
        if H <= 0:
            continue
        # 🔴 본 회차와 **같은 층**을 봐야 한다 — `analyse` 가 공에 45번 3회차의
        #    속도 게이트를 걸므로 여기서도 건다. 안 걸면 층이 달라져 비교가 안 된다.
        ball_t, _ = gate_by_speed(ball_t, H)
        # 본 회차와 같은 주 층 정의를 쓰되, 여기서는 박스를 통째로 들고 있는다.
        for t in range(det["frames"]):
            boxes = cands[t]
            if len(boxes) < 2 or ball_t[t, 2] <= 0:
                continue
            ball = ball_t[t, :2]
            d = [float(np.hypot(*(np.asarray(foot_point(b)) - ball)) / H) for b in boxes]
            ai = int(np.argmin(d))
            if d[ai] > NEAR:
                continue
            areas = [b[2] * b[3] for b in boxes]
            ci = int(np.argmax(areas))
            rows_seen += 1
            cand_counts.append(len(boxes))
            top = areas[ci]
            tie_counts.append(sum(1 for a in areas if a >= top * (1 - TIE)))
            if ci == ai:
                continue
            aspect_chosen.append(boxes[ci][2] / boxes[ci][3])
            aspect_argmin.append(boxes[ai][2] / boxes[ai][3])
            area_ratio.append(areas[ci] / areas[ai])
            height_ratio.append(boxes[ci][3] / boxes[ai][3])
            if boxes[ci][2] >= max(b[2] for b in boxes):
                chosen_is_widest += 1

    n = len(area_ratio)
    print(f"주 층 {rows_seen}프레임 · 불일치 {n}프레임\n")
    if not n:
        print("🔴 불일치가 없다 — 볼 것이 없다")
        return

    def q(v, p):
        s = sorted(v)
        return s[min(len(s) - 1, int(p * (len(s) - 1)))]

    print(f"(a) **거의 동률인가** — 최대 면적의 {TIE:.0%} 안에 든 후보 수")
    print(f"      중앙 {statistics.median(tie_counts):.0f} · "
          f"p75 {q(tie_counts, .75):.0f} · 최대 {max(tie_counts)}  "
          f"(후보 수 중앙 {statistics.median(cand_counts):.0f})")
    print(f"      2명 이상 동률인 프레임: "
          f"{sum(c >= 2 for c in tie_counts)}/{len(tie_counts)} "
          f"({sum(c >= 2 for c in tie_counts)/len(tie_counts):.0%})")

    print(f"\n(b) **넓은 박스가 이기는가** — 가로세로비 (w/h)")
    print(f"      고른 박스   : 중앙 {statistics.median(aspect_chosen):.2f} "
          f"· p75 {q(aspect_chosen, .75):.2f} · 최대 {max(aspect_chosen):.2f}")
    print(f"      최근접 후보 : 중앙 {statistics.median(aspect_argmin):.2f} "
          f"· p75 {q(aspect_argmin, .75):.2f}")
    print(f"      고른 것이 그 프레임에서 **가장 넓은** 박스: "
          f"{chosen_is_widest}/{n} ({chosen_is_widest/n:.0%})")

    print(f"\n(c) **면적비 대 높이비**")
    print(f"      면적비 : 중앙 {statistics.median(area_ratio):.2f} "
          f"· p25 {q(area_ratio, .25):.2f} · p75 {q(area_ratio, .75):.2f}")
    print(f"      높이비 : 중앙 {statistics.median(height_ratio):.2f} "
          f"· p25 {q(height_ratio, .25):.2f} · p75 {q(height_ratio, .75):.2f}")
    print(f"      🔴 면적비가 높이비보다 훨씬 크면 **폭이 이긴 것**이다")

    (HERE / "posthoc_raw.json").write_text(json.dumps({
        "frames": rows_seen, "mismatch": n,
        "tie_counts": tie_counts, "area_ratio": area_ratio,
        "height_ratio": height_ratio, "aspect_chosen": aspect_chosen,
        "aspect_argmin": aspect_argmin, "chosen_is_widest": chosen_is_widest,
    }, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
