"""B-6 A-1 — selector 차이가 downstream feature/grade에 얼마나 전이되는가.

production selector는 `pose.py:_largest_person_box()` = **baseline(면적 최대)** 다.
A-pose·B-pose·continuity는 production에 존재하지 않고 eval_b2의 평가용 구현이다.
B-2에서 baseline 70.1% / A-pose 85.6% / B-pose 87.6% 였는데, 그 격차가 실제
지표와 등급까지 내려오는지를 여기서 확인한다.

읽기 전용이다. production code·selector·weights·rubric·labels·기존 산출물을
수정하지 않는다. 결과는 eval_b6/ 에만 쓴다.

두 트랙으로 나눈다 — **rubric이 있는 클립과 없는 클립이 다르기 때문**이다.

  Track 1: Phase A 39클립 (Kinetics "hitting baseball").
           야구 **타격** rubric이 없으므로 grade를 내지 않는다. feature까지만.
  Track 2: rubric이 실제 존재하는 22클립 (야구 투구 1·농구 2·축구 19).
           여기서만 grade / grade_changed가 의미를 가진다.

Track 1의 kinematic 설정에 대하여
-----------------------------------
feature 산출에는 impact_limb / impact_event가 필요한데 타격 rubric이 없으므로
가져올 곳이 없다. 그래서 **모든 selector에 동일하게** arm / extension_peak을
적용한다(타격은 팔 스윙이므로). 이것은 rubric이 아니고 타격 역학에 대한 주장도
아니다. 목적이 selector **간 차이**의 측정이므로 설정은 공통 상수로 상쇄된다.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

PHASE_A = Path("/mnt/d/supersub-phaseA")
AGENT = Path("/home/ho/projects/super-sub.cloud/agent")
OUT = Path(__file__).resolve().parent

sys.path.insert(0, str(PHASE_A / "eval_b2"))
sys.path.insert(0, str(PHASE_A / "labeling"))
sys.path.insert(0, str(AGENT / "src"))

import eval_b2 as e2  # noqa: E402  (selector 구현 — 읽기 전용 import)
from targets import clip_ids, load_candidates  # noqa: E402

from supersub_agent import features as F  # noqa: E402  (읽기 전용)
from supersub_agent import scoring as S  # noqa: E402
from supersub_agent.pose import (  # noqa: E402
    COCO_PERSON_LABEL,
    PERSON_DETECTOR,
    POSE_MODEL,
    read_frames,
)

MODES = e2.MODES                    # baseline, A, B, A_pose, B_pose
BASE = "baseline"                   # = production _largest_person_box
DET_THRESHOLD = e2.DET_THRESHOLD
MAX_BATCH = 24

# Track 1 전용 — 위 docstring 참고. rubric이 아니다.
T1_LIMB, T1_EVENT = "arm", "extension_peak"

# Track 2 — 영상 파일명 → rubric 키. 동작이 실제로 일치하는 것만 건다.
# 키는 discover_rubrics가 만드는 "<종목>/<동작>" 형식이다.
RUBRIC_FOR = {
    "baseball_pitch_trim.mp4": "baseball/pitching",
    "bball_shot.mp4": "basketball/jump_shot",
    "bball_layup_trim.mp4": "basketball/layup",   # status: draft
}
SOCCER_RUBRIC = "football/instep_shot"            # penalty / freekick = 인스텝 슈팅

# features.extract_features가 실제로 돌려주는 키 (이름을 추측하지 않고 확인함).
FEATURE_KEYS = [
    "impact_frame",
    "swing_knee_angle_at_impact", "plant_knee_angle_at_impact",
    "trunk_forward_lean_deg_at_impact", "hip_rotation_range_deg",
    "swing_hip_flexion_after_impact_deg", "follow_through_duration_frames",
    "swing_elbow_angle_at_impact", "support_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg", "hip_shoulder_separation_deg",
]


def _pose_batch(proc, model, dev, rgb, xywh):
    """한 프레임의 박스 여러 개에 ViTPose를 돌려 (N,17,3)을 돌려준다."""
    batch = MAX_BATCH
    while True:
        try:
            outs = []
            for s in range(0, len(xywh), batch):
                chunk = xywh[s : s + batch]
                inp = proc(rgb, boxes=[chunk], return_tensors="pt").to(dev)
                with torch.inference_mode():
                    o = model(**inp)
                outs.extend(proc.post_process_pose_estimation(o, boxes=[chunk])[0])
            return [
                np.concatenate(
                    [np.asarray(r["keypoints"], dtype=np.float64),
                     np.asarray(r["scores"], dtype=np.float64).reshape(-1, 1)],
                    axis=1,
                )
                for r in outs
            ]
        except torch.cuda.OutOfMemoryError:  # pragma: no cover
            torch.cuda.empty_cache()
            batch = max(1, batch // 2)
            if batch == 1:
                raise


def _downstream(kps: np.ndarray, limb: str, event: str) -> dict:
    """키포인트 하나에서 품질·임팩트·지표를 뽑는다. 실패도 결과로 기록한다."""
    out: dict = {
        "usable_ratio_arm": round(float(F.valid_frames(kps, "arm").mean()), 4),
        "usable_ratio_leg": round(float(F.valid_frames(kps, "leg").mean()), 4),
        "detected_frames": int((kps[:, :, 2] > 0).any(axis=1).sum()),
        "features_ok": 0, "fail_reason": "",
    }
    for k in FEATURE_KEYS:
        out[k] = ""
    try:
        feats = F.extract_features(kps, impact_limb=limb, impact_event=event)
    except (F.InsufficientQuality, ValueError, IndexError) as exc:
        out["fail_reason"] = f"{type(exc).__name__}: {str(exc)[:90]}"
        return out
    out["features_ok"] = 1
    for k in FEATURE_KEYS:
        v = feats.get(k)
        out[k] = round(float(v), 2) if isinstance(v, (int, float)) else ""
    out["_features"] = feats
    return out


def _grade(feats: dict, rubric) -> tuple[str, str]:
    """rubric의 bands로 등급을 낸다 (판정은 코드가 한다 — scoring.grade_for)."""
    try:
        crits = rubric.applicable_criteria(feats)
        judgments = {
            c.id: {"grade": c.grade_for(feats), "evidence": "", "metric_ref": ""}
            for c in crits
        }
        res = S.aggregate(judgments, rubric)
        return str(res["score"]), str(res["grade"])
    except (S.RubricError, ValueError, KeyError) as exc:
        return "", f"ERROR: {type(exc).__name__}"


# ════════════════════════════════════════════════════════════ Track 1
def track1(pproc, pmodel, dev) -> list[dict]:
    pq = e2.load_pq()
    rows = []
    for i, cid in enumerate(clip_ids(), 1):
        per_frame, wh, _ = load_candidates(cid)
        sels = {m: e2.run(per_frame, wh, m, cid, pq) for m in MODES}

        need: dict[int, set[int]] = {}
        for m in MODES:
            for t, (gi, _, _) in enumerate(sels[m]):
                if gi is not None:
                    need.setdefault(t, set()).add(int(gi))

        frames, _, _ = read_frames(str(PHASE_A / "clips" / f"{cid}.mp4"), target_fps=15)
        if len(frames) != len(per_frame):
            raise RuntimeError(f"{cid}: 프레임 {len(frames)} != 후보 {len(per_frame)}")

        kp_cache: dict[tuple[int, int], np.ndarray] = {}
        for t, gis in sorted(need.items()):
            gl = sorted(gis)
            rgb = cv2.cvtColor(frames[t], cv2.COLOR_BGR2RGB)
            xywh = [
                [float(per_frame[t][g][0]), float(per_frame[t][g][1]),
                 float(per_frame[t][g][2] - per_frame[t][g][0]),
                 float(per_frame[t][g][3] - per_frame[t][g][1])]
                for g in gl
            ]
            for g, kp in zip(gl, _pose_batch(pproc, pmodel, dev, rgb, xywh)):
                kp_cache[(t, g)] = kp

        base_res = None
        for m in MODES:
            kps = np.stack([
                kp_cache[(t, int(gi))] if gi is not None else np.zeros((17, 3))
                for t, (gi, _, _) in enumerate(sels[m])
            ])
            res = _downstream(kps, T1_LIMB, T1_EVENT)
            picks = [gi for gi, _, _ in sels[m]]
            if m == BASE:
                base_res, base_picks = res, picks
                diff_frames = 0
            else:
                diff_frames = sum(1 for a, b in zip(base_picks, picks) if a != b)
            row = {
                "track": 1, "clip_id": cid, "rubric": "n/a",
                "production_selector": BASE, "comparison_selector": m,
                "frames": len(per_frame),
                "multi_candidate_frames": sum(
                    1 for b in per_frame if (b[:, 4] >= DET_THRESHOLD).sum() > 1),
                "selected_target_difference": diff_frames,
                "selected_target_difference_ratio": round(diff_frames / len(per_frame), 4),
                **{k: v for k, v in res.items() if not k.startswith("_")},
                "grade": "no_batting_rubric", "grade_changed": "n/a",
            }
            for k in FEATURE_KEYS:
                bv, mv = base_res.get(k, ""), res.get(k, "")
                row[f"delta_{k}"] = (round(float(mv) - float(bv), 2)
                                     if bv != "" and mv != "" else "")
            rows.append(row)
        print(f"[T1 {i}/39] {cid} multi={rows[-1]['multi_candidate_frames']} "
              f"diff(B_pose)={rows[-1]['selected_target_difference']}", flush=True)
    return rows


# ════════════════════════════════════════════════════════════ Track 2
def track2(dproc, dmodel, pproc, pmodel, dev, rubrics) -> list[dict]:
    root = AGENT / "data"
    vids = sorted(root.glob("*.mp4")) + sorted(
        (root / "goldenset" / "soccerkicks_video").glob("*.avi"))
    rows = []
    for vi, p in enumerate(vids, 1):
        rkey = RUBRIC_FOR.get(p.name, SOCCER_RUBRIC if p.suffix == ".avi" else None)
        if rkey is None or rkey not in rubrics:
            print(f"[T2 {vi}/{len(vids)}] {p.name} — rubric 없음, 건너뜀", flush=True)
            continue
        rubric = rubrics[rkey]

        frames, _, _ = read_frames(str(p), target_fps=15)
        prev = {m: None for m in MODES}
        picks = {m: [] for m in MODES}
        kps_seq = {m: [] for m in MODES}
        n_multi = 0

        for fr in frames:
            rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            inp = dproc(images=rgb, return_tensors="pt").to(dev)
            with torch.inference_mode():
                o = dmodel(**inp)
            d = dproc.post_process_object_detection(
                o, target_sizes=[(rgb.shape[0], rgb.shape[1])], threshold=0.3)[0]
            boxes = (np.array([[float(v) for v in b] + [float(s)]
                               for s, l, b in zip(d["scores"], d["labels"], d["boxes"])
                               if int(l) == COCO_PERSON_LABEL and float(s) >= DET_THRESHOLD])
                     if len(d["scores"]) else np.zeros((0, 5)))
            if len(boxes) == 0:
                for m in MODES:
                    picks[m].append(None)
                    kps_seq[m].append(np.zeros((17, 3)))
                    prev[m] = None
                continue
            if len(boxes) >= 2:
                n_multi += 1

            H, W = rgb.shape[:2]
            area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            cx, cy = (boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2
            cen = 1 - np.hypot(cx - W / 2, cy - H / 2) / (0.5 * float(np.hypot(W, H)))
            size = area / area.max()
            xywh = [[float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])]
                    for b in boxes]
            kps_all = _pose_batch(pproc, pmodel, dev, rgb, xywh)
            pqv = np.array([float(k[:, 2].mean()) for k in kps_all])

            for m in MODES:
                if len(boxes) == 1:
                    j = 0
                elif m == BASE:
                    j = int(np.argmax(area))
                else:
                    w = e2.WEIGHTS[m]
                    cont = (np.array([e2.iou(prev[m], b[:4]) for b in boxes])
                            if prev[m] is not None else np.zeros(len(boxes)))
                    s = (w.get("centrality", 0) * cen + w.get("size", 0) * size
                         + w.get("pose_quality", 0) * pqv + w.get("continuity", 0) * cont)
                    j = int(np.argmax(s))
                picks[m].append(j)
                kps_seq[m].append(kps_all[j])
                prev[m] = boxes[j, :4]

        base_res = base_grade = None
        for m in MODES:
            kps = np.stack(kps_seq[m])
            res = _downstream(kps, rubric.impact_limb, rubric.impact_event)
            score, grade = (_grade(res["_features"], rubric)
                            if res.get("_features") is not None else ("", "n/a (feature 실패)"))
            diff = (0 if m == BASE
                    else sum(1 for a, b in zip(picks[BASE], picks[m]) if a != b))
            if m == BASE:
                base_res, base_grade = res, grade
            row = {
                "track": 2, "clip_id": p.name, "rubric": rkey,
                "rubric_status": rubric.status,
                "production_selector": BASE, "comparison_selector": m,
                "frames": len(frames), "multi_candidate_frames": n_multi,
                "selected_target_difference": diff,
                "selected_target_difference_ratio": round(diff / max(1, len(frames)), 4),
                **{k: v for k, v in res.items() if not k.startswith("_")},
                "score": score, "grade": grade,
                "grade_changed": ("n/a" if m == BASE else int(grade != base_grade)),
            }
            for k in FEATURE_KEYS:
                bv, mv = base_res.get(k, ""), res.get(k, "")
                row[f"delta_{k}"] = (round(float(mv) - float(bv), 2)
                                     if bv != "" and mv != "" else "")
            rows.append(row)
        print(f"[T2 {vi}/{len(vids)}] {p.name} [{rkey}] multi={n_multi} "
              f"diff(B_pose)={rows[-1]['selected_target_difference']} "
              f"grade={rows[-1]['grade']}", flush=True)
    return rows


def _write(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    from transformers import AutoProcessor, RTDetrForObjectDetection, VitPoseForPoseEstimation

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    t0 = time.time()
    pproc = AutoProcessor.from_pretrained(POSE_MODEL)
    pmodel = VitPoseForPoseEstimation.from_pretrained(POSE_MODEL).to(dev).eval()

    r1 = track1(pproc, pmodel, dev)
    t1 = time.time()
    _write(OUT / "selector_downstream_comparison.csv", r1)

    dproc = AutoProcessor.from_pretrained(PERSON_DETECTOR)
    dmodel = RTDetrForObjectDetection.from_pretrained(PERSON_DETECTOR).to(dev).eval()
    rubrics = S.discover_rubrics(AGENT / "rubrics")
    r2 = track2(dproc, dmodel, pproc, pmodel, dev, rubrics)
    t2 = time.time()
    _write(OUT / "selector_downstream_rubric_clips.csv", r2)

    # 실행 메타는 파일로 남기지 않는다(승인된 산출물 목록에 없음). 보고서에 적는다.
    print(json.dumps({
        "device": dev,
        "track1_seconds": round(t1 - t0, 1),
        "track2_seconds": round(t2 - t1, 1),
        "total_seconds": round(t2 - t0, 1),
        "track1_clips": len({r["clip_id"] for r in r1}),
        "track2_clips": len({r["clip_id"] for r in r2}),
        "modes": MODES,
        "weights": e2.WEIGHTS,
        "det_threshold": DET_THRESHOLD,
        "track1_kinematics": {"impact_limb": T1_LIMB, "impact_event": T1_EVENT,
                              "note": "rubric 아님. selector 간 비교를 위한 공통 상수."},
    }, ensure_ascii=False, indent=2))
    print(f"\n완료 — Track1 {t1-t0:.0f}s / Track2 {t2-t1:.0f}s / 총 {t2-t0:.0f}s ({dev})")


if __name__ == "__main__":
    main()
