#!/usr/bin/env python3
"""표본을 10건에서 25건으로 — 3회차 설계가 넓은 표본에서 어떻게 구는가.

    uv run python eval/pending18_scale/measure_scale.py    # GPU 불필요

1~3회차가 전부 **같은 3건**으로 판정됐다. 상수를 또 만지면 3건에 맞추는
일이므로, **처방을 고정하고 표본만 늘린다.**

🔴 **판정 회차가 아니다.** 새 15건에는 라벨이 없어 「고쳤는가」를 못 묻는다.
라벨 없이 답할 수 있는 것만 묻는다 — **3회차가 걸린 커버리지 실패가 3건
우연인지 설계의 성질인지.**

닻은 **합성한다**(2000ms 이후 후보 2개 이상인 첫 프레임의 넓이 2위). 내가
그리면 그 그림이 결과를 만든다. 기존 10건은 **사람이 그린 박스 그대로** 써서
앞 회차와 비교가 끊기지 않게 한다. 규격은 `PREREGISTRATION.md`(`1ff5f9d`).

🔴 **`src/` 를 고치지 않는다.**
"""
from __future__ import annotations

import csv
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval" / "phaseA"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_appearance"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_reacquire"))
sys.path.insert(0, str(ROOT / "eval" / "pending18_conservative"))

from labeling.targets import clip_ids, load_candidates  # noqa: E402
from measure_appearance import BOXES, SWITCHING, boxes_from_cache, hist_of, similarity  # noqa: E402
from measure_conservative import TAU, calibrate, track  # noqa: E402
from measure_reacquire import CLIPS, anchor_of, wrong_and_cover  # noqa: E402
from supersub_agent.pose import SubjectRequest, read_frames, select_subject_boxes  # noqa: E402

META = ROOT / "eval" / "phaseA" / "phaseA_metadata.csv"
MIN_MULTI_FRAMES = 100     # 사전 등록: 다인 프레임이 이만큼 있는 클립만
ANCHOR_AFTER_MS = 2000.0   # 사전 등록: 기존 10건의 at_ms 대에 맞춘다


def multi_frames(clip: str) -> int:
    per, _wh, _fps = load_candidates(clip)
    return sum(1 for a in per
               if sum(1 for *_r, s in a if float(s) >= 0.5) >= 2)


def synthetic_anchor(clip: str):
    """(정규화 박스, at_ms) — 2000ms 이후 후보 2개 이상인 첫 프레임의 **넓이 2위**.

    🔴 1위는 자동 선택이 고르는 것이라, 2위를 골라야 **지정이 실제로 일을 한다**.
    """
    _auto, cands, wh, fps = boxes_from_cache(clip)
    start = int(round(ANCHOR_AFTER_MS / 1000.0 * fps))
    W, H = wh
    for t in range(max(0, start), len(cands)):
        here = sorted(cands[t], key=lambda b: b[2] * b[3], reverse=True)
        if len(here) >= 2:
            x, y, bw, bh = here[1]
            return (x / W, y / H, bw / W, bh / H), t / fps * 1000.0
    return None, None


def main() -> None:
    if not CLIPS.exists():
        raise SystemExit(f"🔴 클립을 찾을 수 없다: {CLIPS}")

    meta = {r["clip_id"]: r.get("single_or_multi", "").strip()
            for r in csv.DictReader(open(META, encoding="utf-8"))}

    # --- 표본 구성 -------------------------------------------------------
    sample: list[tuple[str, tuple, float, str, bool]] = []   # clip, box, at_ms, 주석, 사람이_그림
    for clip in clip_ids():
        if multi_frames(clip) < MIN_MULTI_FRAMES:
            continue
        if clip in BOXES:
            box, at_ms = BOXES[clip]
            sample.append((clip, box, at_ms, meta.get(clip, "?"), True))
        else:
            box, at_ms = synthetic_anchor(clip)
            if box is not None:
                sample.append((clip, box, at_ms, meta.get(clip, "?"), False))

    drawn = sum(1 for *_r, human in sample if human)
    print(f"표본 {len(sample)}건 — 사람이 그린 닻 {drawn}건 · 합성 닻 "
          f"{len(sample) - drawn}건 (다인 프레임 ≥{MIN_MULTI_FRAMES})\n")

    K = calibrate()
    print(f"→ K = {K}   (🔴 보정용은 기존 「깨끗한 7건」 그대로다 — 새 표본을 "
          f"넣으면 늘린 의미가 사라진다)\n")

    print("═" * 96)
    print(f"  {'clip':16s} {'주석':6s} {'닻':4s} │ {'엉뚱(현)':>8s} {'엉뚱(3회차)':>11s} "
          f"{'변화':>6s} │ {'커버 유지':>8s} │ 재획득")
    print("═" * 96)

    low_cover, worse, rows = [], [], []
    for clip, box, at_ms, ann, human in sample:
        auto, cands, wh, fps = boxes_from_cache(clip)
        frames, _sf, _s = read_frames(CLIPS / f"{clip}.mp4")
        subject = SubjectRequest(box=box, at_ms=at_ms)
        base, _sel = select_subject_boxes(auto, cands, subject, fps, wh)
        anchor, _seed, ah = anchor_of(auto, cands, frames, subject, fps, wh)
        if anchor is None:
            print(f"  {clip:16s} {ann:6s} {'사람' if human else '합성':4s} │ "
                  f"닻 실패 (IoU < 최소) — 건너뜀")
            continue
        new, reacq = track(auto, cands, frames, subject, fps, wh, K)
        w0, c0 = wrong_and_cover(base, frames, ah)
        w1, c1 = wrong_and_cover(new, frames, ah)
        drop = (1.0 - w1 / w0) if w0 else 0.0
        keep = (c1 / c0) if c0 else 0.0
        if keep < 0.50:
            low_cover.append(clip)
        if w1 > w0:
            worse.append(clip)
        rows.append((clip, human, drop, keep, w0))
        mark = " 🔴" if keep < 0.50 else ""
        print(f"  {clip:16s} {ann:6s} {'사람' if human else '합성':4s} │ "
              f"{w0:8d} {w1:11d} {drop:5.0%} │ {keep:7.0%}{mark} │ {reacq}")

    # --- 사전 등록이 보고하라고 한 넷 ------------------------------------
    print("\n" + "═" * 96)
    print("사전 등록이 보고하라고 한 것")
    print("═" * 96)

    n = len(rows)
    print(f"  2) 커버리지 50% 미만으로 떨어진 클립: **{len(low_cover)}/{n}**"
          + (f" — {', '.join(low_cover)}" if low_cover else ""))
    print("     예측: 「3회차 D 실패가 우연이 아니면 여럿 나온다」 → "
          + ("✅ 예측대로 여럿 나왔다" if len(low_cover) >= 3 else
             "🔴 예측이 빗나갔다 — 3건에서만 났던 일이다"))

    print(f"  3) 엉뚱 프레임이 **는** 클립: {len(worse)}"
          + (f" — {', '.join(worse)}" if worse else " (없다)"))

    old = [r for r in rows if r[1]]
    new_ = [r for r in rows if not r[1]]
    print("  4) 기존 10건 대 새 표본 — 분포가 다른가")
    for label, group in (("기존(사람 닻)", old), ("새로(합성 닻)", new_)):
        if not group:
            continue
        drops = [d for _c, _h, d, _k, w in group if w]
        keeps = [k for *_r, k, _w in group]
        print(f"     {label:14s} n={len(group):2d} · 엉뚱 감소 중앙 "
              f"{st.median(drops) if drops else float('nan'):.0%} · "
              f"커버 유지 중앙 {st.median(keeps):.0%} · "
              f"커버<50% {sum(1 for k in keeps if k < 0.5)}건")

    print("\n" + "═" * 96)
    print("🔴 판정 회차가 아니다. 새 표본에는 라벨이 없어 「고쳤는가」는 못 묻는다.")
    print("🔴 합성 닻은 「옳은 사람」이 아니다 — 「고른 사람을 따라가는가」만 잰다.")
    print("🔴 이 회차도 `src/` 를 고치지 않는다.")


if __name__ == "__main__":
    main()
