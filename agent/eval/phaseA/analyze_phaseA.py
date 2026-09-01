"""Phase A 분석 — 캐시된 포즈로 게이트·지표·rotation peak을 산출한다.

production code는 import만 하고 수정하지 않는다.
rotation_peak은 여기서만 계산한다 (production IMPACT_EVENTS에 넣지 않는다).
"""
import sys, json, csv
from pathlib import Path
import numpy as np

sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import features as F

ROOT = Path("/mnt/d/supersub-phaseA")
CACHE = ROOT/"cache"

JOINTS = {"shoulder": [F.L_SHOULDER, F.R_SHOULDER], "elbow": [F.L_ELBOW, F.R_ELBOW],
          "wrist": [F.L_WRIST, F.R_WRIST], "hip": [F.L_HIP, F.R_HIP],
          "knee": [F.L_KNEE, F.R_KNEE], "ankle": [F.L_ANKLE, F.R_ANKLE]}

METRICS = ["hip_shoulder_separation_deg", "hip_rotation_range_deg",
           "trunk_forward_lean_deg_at_impact", "plant_knee_angle_at_impact",
           "swing_knee_angle_at_impact", "swing_elbow_angle_at_impact",
           "support_elbow_angle_at_impact", "swing_shoulder_flexion_after_impact_deg",
           "swing_hip_flexion_after_impact_deg", "follow_through_duration_frames",
           "impact_frame"]


def load(cid):
    d = np.load(CACHE/f"{cid}.npz")
    objs = {k[4:]: d[k] for k in d.files if k.startswith("obj_")}
    return d["keypoints"], float(d["sampled_fps"]), objs


def rotation_peak_candidate(kps):
    """어깨 축 회전 각속도가 최대인 프레임 — READ-ONLY 분석 전용.

    _axis_deg로 mod 180 축각을 얻고, 축이 충분히 보이는 프레임만 후보로 둔다
    (features.MIN_AXIS_LENGTH와 같은 규약). 언랩 후 |d/dt|의 최대를 취한다.
    """
    norm = F.normalize(kps)
    xy = norm[:, :, :2]
    sh_axis = F._axis_deg(xy[:, F.L_SHOULDER] - xy[:, F.R_SHOULDER])
    hip_axis = F._axis_deg(xy[:, F.L_HIP] - xy[:, F.R_HIP])
    ok = ((norm[:, [F.L_SHOULDER, F.R_SHOULDER], 2] >= F.MIN_CONFIDENCE).all(axis=1)
          & (np.linalg.norm(xy[:, F.L_SHOULDER] - xy[:, F.R_SHOULDER], axis=1) >= F.MIN_AXIS_LENGTH))
    hip_ok = ((norm[:, [F.L_HIP, F.R_HIP], 2] >= F.MIN_CONFIDENCE).all(axis=1)
              & (np.linalg.norm(xy[:, F.L_HIP] - xy[:, F.R_HIP], axis=1) >= F.MIN_AXIS_LENGTH))
    out = {"axis_ok_ratio": float(ok.mean()), "hip_axis_ok_ratio": float(hip_ok.mean())}
    if ok.sum() < 4:
        out["peak_frame"] = None; out["n_peaks"] = 0; return out, None
    idx = np.where(ok)[0]
    unw = np.unwrap(sh_axis[idx], period=180.0)
    vel = np.abs(np.gradient(unw))
    peak_local = int(np.argmax(vel))
    peak = int(idx[peak_local])
    # 다중 peak: 최대의 60% 이상이고 서로 3프레임 이상 떨어진 국소 최대
    thr = vel.max() * 0.6
    cand = [i for i in range(1, len(vel)-1)
            if vel[i] >= thr and vel[i] >= vel[i-1] and vel[i] >= vel[i+1]]
    merged = []
    for c in cand:
        if not merged or idx[c] - idx[merged[-1]] > 3: merged.append(c)
    out.update(peak_frame=peak, peak_vel=float(vel.max()),
               n_peaks=len(merged), peak_pos=float(peak/(len(kps)-1)),
               shoulder_rot_range=float(np.ptp(unw)),
               hip_rot_range=float(np.ptp(np.unwrap(hip_axis[np.where(hip_ok)[0]], period=180.0)))
                             if hip_ok.sum() >= 2 else None)
    return out, peak


def analyze(cid):
    kps, fps, objs = load(cid)
    T = len(kps)
    row = {"clip_id": cid, "frames": T, "sampled_fps": round(fps, 2),
           "person_ratio": round(float((kps[:, :, 2].max(axis=1) > 0).mean()), 3)}

    for name, ids in JOINTS.items():
        c = kps[:, ids, 2]
        row[f"q_{name}_mean"] = round(float(c.mean()), 3)
        row[f"q_{name}_ok"] = round(float((c >= 0.3).all(axis=1).mean()), 3)

    row["valid_arm_ratio"] = round(float(F.valid_frames(kps, "arm").mean()), 3)
    row["valid_leg_ratio"] = round(float(F.valid_frames(kps, "leg").mean()), 3)

    norm = F.normalize(kps)
    for limb in ("arm", "leg"):
        sw, _ = F.identify_limb(norm, limb)
        row[f"auto_{limb}_side"] = "left" if sw == F.LIMB_CHAINS[limb]["left"] else "right"
        try:
            row[f"gate_{limb}"] = round(F.check_quality(kps, limb=limb), 3)
        except F.InsufficientQuality:
            row[f"gate_{limb}"] = None
        for side in ("left", "right"):
            try:
                row[f"gate_{limb}_{side}"] = round(F.check_quality(kps, limb=limb, side=side), 3)
            except F.InsufficientQuality:
                row[f"gate_{limb}_{side}"] = None

    rp, _ = rotation_peak_candidate(kps)
    for k, v in rp.items():
        row[f"rp_{k}"] = round(v, 3) if isinstance(v, float) else v

    for name in ("baseball_bat", "sports_ball", "tennis_racket"):
        tr = objs.get(name)
        row[f"obj_{name}"] = round(float((tr[:, 2] > 0).mean()), 3) if tr is not None else None
        row[f"obj_{name}_hi"] = int((tr[:, 2] >= 0.8).sum()) if tr is not None else None

    feats = {}
    for tag, (limb, event, side) in {
        "arm_ext_auto": ("arm", "extension_peak", "auto"),
        "arm_ext_left": ("arm", "extension_peak", "left"),
        "arm_ext_right": ("arm", "extension_peak", "right"),
        "leg_ext_auto": ("leg", "extension_peak", "auto"),
        "arm_apex_auto": ("arm", "distal_apex", "auto"),
    }.items():
        try:
            f = F.extract_features(kps, objs, impact_limb=limb, impact_event=event, swing_side=side)
            feats[tag] = {"ok": True, **f}
        except (F.InsufficientQuality, ValueError) as e:
            feats[tag] = {"ok": False, "err": f"{type(e).__name__}: {e}"}
    return row, feats


def main():
    cids = sorted(p.stem for p in CACHE.glob("*.npz") if ".ERROR" not in p.name)
    rows, allf = [], {}
    for cid in cids:
        try:
            r, f = analyze(cid)
        except Exception as e:
            print(f"ERR {cid}: {type(e).__name__}: {e}"); continue
        rows.append(r); allf[cid] = f
    keys = sorted({k for r in rows for k in r})
    keys = ["clip_id"] + [k for k in keys if k != "clip_id"]
    with open(ROOT/"phaseA_pose.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    (ROOT/"phaseA_features.json").write_text(json.dumps(allf, ensure_ascii=False, indent=1))
    print(f"analyzed {len(rows)} clips -> phaseA_pose.csv / phaseA_features.json")


if __name__ == "__main__":
    main()
