"""Phase B-4 검수 대상 선정 + blind form 생성.

두 가지를 한다.
 (1) 이미 GT가 있는 A/B 불일치 프레임에서 'B-pose의 우위가 어디서 오는가'를 추적한다.
     B-pose가 현재 정체성을 **언제 획득했는지**(직전 switch 시점)를 되짚어,
     그 시점에 A-pose와 같은 사람을 보고 있었는지 확인한다. 같았다면 그 프레임의
     승패는 'B가 옳은 사람을 찾았다'가 아니라 'A가 이탈했다'가 된다.
 (2) 남은 불일치 프레임에서 정보량이 높은 검수 후보를 뽑아 blind form을 만든다.
     같은 run(연속 불일치 구간) 안의 프레임은 거의 중복이므로 run당 1개만 쓴다.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/mnt/d/supersub-phaseA")
B2 = ROOT / "eval_b2"
B4 = ROOT / "eval_b4"

sys.path.insert(0, str(B2))
sys.path.insert(0, str(ROOT / "labeling"))
from targets import enumerate_targets, load_candidates, target_key  # noqa: E402

import eval_b2 as e2  # noqa: E402

MIN_BOX_FRAC = 0.015    # 육안 판별 하한
PER_CLIP_CAP = 4
TARGET_N = 60

rows = list(csv.DictReader(open(B4 / "ab_disagreement_frames.csv")))
labeled = [r for r in rows if r["gt_source"] in ("labels.json", "ai_reviewed")]


# ---------------------------------------------------------------- (1) 기원 추적
def trace_origin() -> list[dict]:
    pq = e2.load_pq()
    out = []
    for r in sorted(labeled, key=lambda x: (x["clip_id"], int(x["frame"]))):
        cid, f = r["clip_id"], int(r["frame"])
        per_frame, wh, _ = load_candidates(cid)
        sa = e2.run(per_frame, wh, "A_pose", cid, pq)
        sb = e2.run(per_frame, wh, "B_pose", cid, pq)

        # B-pose가 지금 보고 있는 사람을 획득한 시점 = 직전 switch
        origin = 0
        for t in range(f, 0, -1):
            if sb[t][1] is None or sb[t - 1][1] is None:
                origin = t
                break
            if e2.iou(sb[t - 1][1], sb[t][1]) < e2.SWITCH_IOU:
                origin = t
                break
        agreed = "" if sa[origin][0] is None else int(sa[origin][0] == sb[origin][0])
        # 불일치가 시작된 시점
        first_diff = f
        for t in range(f, 0, -1):
            if sa[t - 1][0] is None or sb[t - 1][0] is None or sa[t - 1][0] == sb[t - 1][0]:
                first_diff = t
                break
        out.append({
            "clip_id": cid, "ratio": r["ratio"], "frame": f,
            "old_gt": r["old_gt"], "ai_gt": r["ai_gt"], "ai_conf": r["ai_conf"],
            "a_pose_box": r["a_pose_box"], "b_pose_box": r["b_pose_box"],
            "a_correct_old": r["a_correct_old"], "b_correct_old": r["b_correct_old"],
            "winner": ("B-pose" if r["b_correct_old"] == "1" else
                       "A-pose" if r["a_correct_old"] == "1" else "둘 다 오답/판정불가"),
            "b_identity_origin_frame": origin,
            "b_continuity_here": r["b_pose_continuity"],
            "a_agreed_at_origin": agreed,
            "divergence_start_frame": first_diff,
            "divergence_len_to_here": f - first_diff + 1,
            "interpretation": ("A-pose가 이탈 (B는 유지만 함)" if agreed == 1
                               else "B가 독자적으로 다른 사람을 획득" if agreed == 0
                               else "판정 불가"),
        })
    with open(B4 / "ab_origin_trace.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    return out


# ---------------------------------------------------------------- (2) 검수 후보
def pick_candidates() -> list[dict]:
    pool = [r for r in rows
            if r["different_person"] == "1"
            and float(r["min_box_frac"]) >= MIN_BOX_FRAC
            and r["gt_source"] not in ("labels.json", "ai_reviewed")]

    # run당 대표 1개 (info_score 최대, 동점이면 run 중앙에 가까운 프레임)
    by_run = defaultdict(list)
    for r in pool:
        by_run[(r["clip_id"], r["run_len"], _run_key(r))].append(r)
    reps = [max(v, key=lambda r: (float(r["info_score"]), -abs(int(r["frame"]))))
            for v in by_run.values()]

    reps.sort(key=lambda r: -float(r["info_score"]))
    chosen, per_clip = [], defaultdict(int)
    for r in reps:
        if per_clip[r["clip_id"]] >= PER_CLIP_CAP:
            continue
        chosen.append(r)
        per_clip[r["clip_id"]] += 1
        if len(chosen) >= TARGET_N:
            break
    return chosen


def _run_key(r) -> int:
    """같은 run에 속한 프레임을 하나로 묶기 위한 키 (run 시작 프레임)."""
    return int(r["frame"]) - _offset_in_run(r)


_offsets: dict = {}


def _offset_in_run(r) -> int:
    cid = r["clip_id"]
    if cid not in _offsets:
        fr = sorted(int(x["frame"]) for x in rows if x["clip_id"] == cid)
        off, start, prev = {}, None, None
        for f in fr:
            if prev is None or f != prev + 1:
                start = f
            off[f] = f - start
            prev = f
        _offsets[cid] = off
    return _offsets[cid][int(r["frame"])]


def main() -> None:
    tr = trace_origin()
    print("=== (1) GT 있는 A/B 불일치 기원 추적 ===")
    for r in tr:
        print(f"  {r['clip_id']}@{r['ratio']} f{r['frame']:3d}  승자 {r['winner']:14s} "
              f"B정체성획득 f{r['b_identity_origin_frame']:3d}  "
              f"그때 A도 같은사람? {r['a_agreed_at_origin']}  → {r['interpretation']}")

    chosen = pick_candidates()
    print(f"\n=== (2) 검수 후보 {len(chosen)}건 "
          f"(클립 {len({c['clip_id'] for c in chosen})}개) ===")

    # 회귀 케이스는 A/B 불일치 여부와 무관하게 별도 유지한다.
    # (LhD_fnHt_xg 2건은 A-pose·B-pose가 **같이** 틀리므로 불일치 목록에는 없다.
    #  A/B 판별에는 못 쓰지만 failure mode 추적 대상으로는 남겨야 한다.)
    b2f = defaultdict(dict)
    for r in csv.DictReader(open(B2 / "selector_eval_frames.csv")):
        b2f[(r["clip_id"], r["ratio"])][r["selector"]] = r
    disag = {(r["clip_id"], r["ratio"]) for r in rows if r["ratio"]}
    reg = []
    for cid, ratio in (("LhD_fnHt_xg", "0.50"), ("LhD_fnHt_xg", "0.80"),
                       ("N5zWQkoLM3M", "0.50")):
        s = b2f[(cid, ratio)]
        reg.append({
            "clip_id": cid, "ratio": ratio, "frame": s["baseline"]["frame"],
            "n_candidates": s["baseline"]["num_candidates"],
            "n_candidates_ge50": s["baseline"]["num_candidates_ge50"],
            "gt_box_index": s["baseline"]["gt_box_index"],
            **{f"{m}_box": s[m]["selected_box_index"] for m in e2.MODES},
            **{f"{m}_correct": s[m]["correct"] for m in e2.MODES},
            "b_pose_continuity": s["B_pose"]["continuity"],
            "ab_pose_disagree": int((cid, ratio) in disag),
            "discriminates_a_vs_b": int((cid, ratio) in disag),
            "failure_mode": ("continuity가 오답 대상에 고착" if (cid, ratio) in disag
                             else "A-pose·B-pose 공통 실패 (A/B 판별에는 무효)"),
        })
    with open(B4 / "regression_watchlist.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(reg[0]))
        w.writeheader()
        w.writerows(reg)

    # blind form — selector 정보는 한 칸도 넣지 않는다
    form = []
    for r in sorted(chosen, key=lambda x: (x["clip_id"], int(x["frame"]))):
        form.append({
            "clip_id": r["clip_id"],
            "frame": r["frame"],
            "n_candidates": r["n_candidates"],
            "image": f"eval_b4/review_cases/{r['clip_id']}@f{int(r['frame']):03d}.jpg",
            "human_box_index": "",
            "human_note": "",
        })
    with open(B4 / "b4_review_input.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(form[0]))
        w.writeheader()
        w.writerows(form)

    # 우선순위 근거는 검수자에게 주지 않는 별도 파일에 남긴다
    with open(B4 / "b4_selection_rationale.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(chosen[0]))
        w.writeheader()
        w.writerows(sorted(chosen, key=lambda x: -float(x["info_score"])))

    per_clip = defaultdict(int)
    for c in chosen:
        per_clip[c["clip_id"]] += 1
    print("  클립별:", dict(sorted(per_clip.items(), key=lambda kv: -kv[1])))
    print(f"  blind form -> b4_review_input.csv ({len(form)}행, selector 열 없음)")
    print(f"  근거 -> b4_selection_rationale.csv (검수자에게 주지 않음)")
    print(f"  regression watchlist -> regression_watchlist.csv ({len(reg)}행)")


if __name__ == "__main__":
    main()
