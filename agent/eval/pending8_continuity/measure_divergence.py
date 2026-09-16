"""continuity 가 **어디서 갈리고 얼마나 오래 가는가** (미결 `ho` 8번 3회차).

    uv run python eval/pending8_continuity/measure_divergence.py --out <csv>

판정 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md) 에 **돌리기 전에** 굳혔다.

🔴 **`eval_b2.py` 를 import 만 한다.** 그 파일의 `WEIGHTS`·`run()` 이 selector
동작 기준이고, 고치면 **B-2~B-5 결과 전체가 무효**다. 규칙을 복사하지도 않는다 —
복사본은 원본과 갈린다(미결 10번의 형태).

🔴 **분모는 다중후보 프레임뿐이다.** 후보가 하나면 `run()` 이 그것을 강제로
고르므로 selector 를 재는 프레임이 아니다 — `O2GSaYqH8JY` 가 정확히 그 함정이었다
(라벨된 세 프레임이 전부 단일후보라 「5종 전부 정답」이 나왔다).
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
PHASEA = HERE.parent / "phaseA"
sys.path.insert(0, str(PHASEA))
sys.path.insert(0, str(PHASEA / "eval_b2"))
sys.path.insert(0, str(PHASEA / "labeling"))

import eval_b2 as e2  # noqa: E402  (읽기 전용 import — 보존 자산)
from targets import clip_ids, load_candidates  # noqa: E402

#: 야구(Phase A) 표본에서 비교하는 짝 — 저장된 B-2 산출이 이 둘을 적어 두었다.
PAIR = ("A_pose", "B_pose")

#: 🔴 **축구(SoccerNet) 표본에서 비교하는 짝** (2026.09.16, 사용자 지시로 표본을
#: 축구로 옮기며 추가). `A`/`B` 는 **continuity 항 하나만** 다르고 나머지는 같은
#: 기하 가중치다 — continuity 를 격리해 보기에는 오히려 이쪽이 깨끗하다.
#: 그리고 `pose_quality` 를 안 써서 **ViTPose 를 안 돌려도 된다**(검출만).
PAIR_GEOM = ("A", "B")


def runs_of_true(flags: list[bool]) -> list[int]:
    """연속으로 참인 구간들의 길이."""
    out, n = [], 0
    for f in flags:
        if f:
            n += 1
        elif n:
            out.append(n); n = 0
    if n:
        out.append(n)
    return out


def instrument_check(sels_by_clip: dict) -> tuple[int, int]:
    """🔴 기준 A — 저장된 B-2 산출의 선택을 **그대로 재현**하는가.

    `selector_eval_frames.csv` 는 라벨 프레임에서 selector 별
    `selected_box_index` 를 적어 두었다. 내 재구성이 그것과 다르면 **나는 다른
    것을 재고 있는 것**이고, 그러면 아래 숫자는 아무 뜻이 없다.
    """
    checked = agree = 0
    with open(PHASEA / "eval_b2" / "selector_eval_frames.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["selector"] not in PAIR:
                continue
            sel = sels_by_clip.get(row["clip_id"])
            if sel is None:
                continue
            t = int(row["frame"])
            mine = sel[row["selector"]][t][0]
            stored = row["selected_box_index"]
            stored = None if stored == "" else int(stored)
            checked += 1
            agree += int(mine == stored)
    return agree, checked


def soccernet_candidates():
    """축구 방송 클립에서 **검출만** 돌려 `eval_b2.run` 이 먹는 모양으로 만든다.

    🔴 **`_eligible_person_boxes` 를 쓴다** — 후보의 뜻이 selector 와 갈리지 않게
    같은 문턱(`PERSON_ELIGIBLE_THRESHOLD`)을 쓰는 함수다. 그 함수를 통과한 박스는
    이미 「후보」이므로 점수 열을 **1.0** 으로 채운다(`eval_b2.run` 이 그 열로
    다시 거르는데, 두 번 거르면 문턱이 두 곳에 생긴다).
    """
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    sys.path.insert(0, str(HERE.parent / "pending18_ball_proximity"))
    import torch  # noqa: F401
    from measure_proximity import detect_clip  # noqa: E402
    from supersub_agent.pose import _load_detector  # noqa: E402
    import paths  # noqa: E402

    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    det_pair = _load_detector(device)
    for clip in sorted(paths.soccernet_clips_root().rglob("*.mp4")):
        det = detect_clip(clip, det_pair, device)
        per_frame, wh = [], None
        for boxes in det["cands"]:
            arr = np.array([[x, y, x + w, y + h, 1.0] for x, y, w, h in boxes],
                           dtype=float) if boxes else np.zeros((0, 5))
            per_frame.append(arr)
        # 화면 크기 — 중앙성 계산에 쓴다. 검출 박스의 최대 좌표로 잡으면
        # 클립마다 달라지므로 영상에서 직접 읽는다.
        cap = cv2.VideoCapture(str(clip))
        wh = (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        yield clip.stem, per_frame, wh


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--sample", choices=("phasea", "soccernet"), default="phasea",
                    help="phasea = 야구 39클립(저장된 B-2 대조 가능) · "
                         "soccernet = 축구 방송 40편(검출을 새로 돌린다)")
    args = ap.parse_args()

    football = args.sample == "soccernet"
    pair = PAIR_GEOM if football else PAIR
    pq = {} if football else e2.load_pq()
    rows, sels_by_clip = [], {}

    source = (soccernet_candidates() if football else
              ((cid, *load_candidates(cid)[:2]) for cid in clip_ids()))

    for cid, per_frame, wh in source:
        sels = {m: e2.run(per_frame, wh, m, cid, pq) for m in pair}
        sels_by_clip[cid] = sels

        multi, diverge = [], []
        first_multi = first_split = None
        for t, boxes_all in enumerate(per_frame):
            n50 = int((boxes_all[:, 4] >= e2.DET_THRESHOLD).sum())
            a, b = sels[pair[0]][t][0], sels[pair[1]][t][0]
            if n50 < 2:
                continue  # 선택이 강제된 프레임 — 분모에서 뺀다
            multi.append(t)
            if first_multi is None:
                first_multi = t
            split = a != b
            diverge.append(split)
            if split and first_split is None:
                first_split = t

        lens = runs_of_true(diverge)
        rows.append({
            "clip_id": cid,
            "frames": len(per_frame),
            "multi_frames": len(multi),
            "diverge_frames": sum(diverge),
            "diverge_rate": round(sum(diverge) / len(multi), 4) if multi else "",
            "runs": len(lens),
            "run_len_max": max(lens) if lens else 0,
            "run_len_median": round(statistics.median(lens), 1) if lens else 0,
            "first_multi_frame": first_multi if first_multi is not None else "",
            "first_split_frame": first_split if first_split is not None else "",
            "split_at_anchor": int(first_split is not None and first_split == first_multi),
            "selectors": "/".join(pair),
            f"switch_rate_{pair[0]}": e2.switch_rate(sels[pair[0]]),
            f"switch_rate_{pair[1]}": e2.switch_rate(sels[pair[1]]),
        })
        print(f"  {cid}: 다중후보 {len(multi):4d} · 갈림 {sum(diverge):4d} "
              f"· 구간 {len(lens)}", flush=True)

    agree, checked = (0, 0) if football else instrument_check(sels_by_clip)
    if football:
        print("\n[기준 A · 계기 검사] 축구 표본에는 저장된 참조가 없다 — "
              "대신 같은 클립을 두 번 돌려 같은지 본다(아래)")
    else:
        print(f"\n[기준 A · 계기 검사] 저장된 B-2 선택 재현: {agree}/{checked}")
    if not football and agree != checked:
        print("🔴 재현이 안 된다 — 사전 등록대로 아래 숫자를 판정에 쓰지 않는다")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    # --- 사전 등록한 판정선 ---
    usable = [r for r in rows if r["multi_frames"] >= 10]   # 기준 D
    thin = [r for r in rows if r["multi_frames"] < 10]
    split = [r for r in usable if r["diverge_frames"] > 0]
    at_anchor = [r for r in split if r["split_at_anchor"]]
    mid = [r for r in split if not r["split_at_anchor"]]

    print(f"\n클립 {len(rows)} · 분모 10 이상 {len(usable)} · 얇아서 비율 제외 {len(thin)}")
    print(f"  갈린 클립 {len(split)}/{len(usable)}")
    if split:
        print(f"  [B] 첫 갈림이 첫 다중후보 프레임: {len(at_anchor)}/{len(split)} "
              f"({len(at_anchor)/len(split):.0%}) — 판정선 >50%")
        print(f"  [C] 중간에 새로 갈린 클립: {len(mid)}/{len(split)}")
        rates = [r["diverge_rate"] for r in usable if r["diverge_rate"] != ""]
        print(f"  갈림 비율 중앙 {statistics.median(rates):.1%} · 최대 {max(rates):.1%}")
        allruns = [r["run_len_max"] for r in split]
        print(f"  [M2] 최장 갈림 구간 중앙 {statistics.median(allruns):.0f}프레임 "
              f"· 최대 {max(allruns)}프레임")
    for m in pair:
        vals = [r[f"switch_rate_{m}"] for r in rows if r[f"switch_rate_{m}"] is not None]
        print(f"  [M4] {m} 전환율 평균 {statistics.mean(vals):.1%}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
