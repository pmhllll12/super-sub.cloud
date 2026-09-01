"""Phase A 클립 메타데이터 표 — 자동 산출 + 육안 검증(20건) 병합."""
import csv, json
from pathlib import Path
ROOT = Path("/mnt/d/supersub-phaseA")

# 육안 검증 20건 (컨택트시트 판독). peak_verdict:
#   hit=컨택트 ±1프레임, near=1~2프레임 어긋남, late=2~4프레임 늦음,
#   miss=타격 구간 밖/다른 피사체, unusable=대상 자체를 못 봄
VISUAL = {
 "0Fet8TyoNR4": ("측면","단일","큼","완전","명확","명확","hit","유아 티볼. 스윙이 클립 앞 11%에 있음"),
 "3R1kvNrGJK0": ("사선","다인","작음","완전","가림","미검출","miss","펜스 너머. 심판/포수를 피사체로 잡음"),
 "8gmHKqDxXdg": ("측면","단일","큼","반복","명확","명확","miss","실내 티 드릴, 10초에 스윙 여러 번(240x180 10fps)"),
 "GS-PcxmaHmQ": ("사선","다인","중간","반복","명확","명확","miss","케이지 2인. peak가 로드 자세"),
 "Fz16t9SrF3U": ("측면","다인","작음","완전","가림","미검출","unusable","펜스 가림 + 원거리"),
 "Atzrde5uGcM": ("사선","다인","중간","완전","명확","가림","hit","유소년 경기. 배경에 관중 다수"),
 "YNMHMKb5Md4": ("후측면","단일","큼","완전","명확","미검출","hit","도심 배팅케이지, 단일 피사체"),
 "V_whuvMjg_8": ("후면","단일","중간","반복","명확","명확","near","세로영상 실내케이지, 스윙 여러 번"),
 "C7icGyrdROM": ("측면","단일","큼","반복","명확","명확","hit","교습 영상, 스윙 여러 번(320x266)"),
 "O2GSaYqH8JY": ("측면","다인","중간","완전","가림","명확","miss","공 줍는 코치를 피사체로 잡음"),
 "IYFifBJ9lH8": ("사선","다인","작음","불명","미검출","미검출","unusable","실내 트랙. 라벨 의심(투구로 보임)"),
 "LhD_fnHt_xg": ("사선","단일","작음","반복","가림","미검출","unusable","네트 뒤 원거리"),
 "ihWykL5mYRI": ("정면","단일","큼","반복","명확","가림","late","정면 구도. peak가 피니시(2~3프레임 늦음)"),
 "ZMy0t-CSZiU": ("측면","다인","큼","완전","명확","미검출","hit","방송 슬로모션(PastimeAthletics)"),
 "gg5xRWjw3f8": ("측면","단일","중간","불명","명확","미검출","miss","peak가 대기 자세"),
 "cDRi9AzrapA": ("측면","다인","큼","반복","명확","미검출","miss","방송 교습영상, 컷 편집 + 반복"),
 "xMIUw5mi3Eo": ("측면","다인","중간","완전","명확","명확","late","슬로모션. peak 3~4프레임 늦음, 포수 큼"),
 "h_3LqD2Pl-E": ("사선","단일","큼","반복","명확","명확","near","앞 33프레임이 타이틀 카드(사람 없음)"),
 "sGKeqfxwq5E": ("측면","다인","중간","완전","명확","가림","hit","경기 영상, 타자·포수·심판"),
 "w-AQcjcoDyA": ("측면","단일","해당없음","불명","가림","미검출","unusable","신발 클로즈업. 타자가 피사체가 아님"),
}

pose = {r["clip_id"]: r for r in csv.DictReader(open(ROOT/"phaseA_pose.csv"))}
spec = {r["clip_id"]: r for r in csv.DictReader(open(ROOT/"clip_specs.csv"))}
alt  = {r["clip_id"]: r for r in csv.DictReader(open(ROOT/"alt_events.csv"))}
feats= json.loads((ROOT/"phaseA_features.json").read_text())

def num(v):
    return None if v in ("","None",None) else float(v)

out=[]
for cid in sorted(pose):
    p,s,a = pose[cid], spec[cid], alt[cid]
    v = VISUAL.get(cid)
    sc = num(a["subject_scale"])
    gate_arm = any(num(p[f"gate_arm_{k}"]) is not None for k in ("left","right"))
    row = {
      "clip_id": cid,
      "resolution": f"{s['w']}x{s['h']}",
      "fps": s["fps"],
      "camera_angle": v[0] if v else "미검증",
      "player_scale": v[2] if v else ("작음" if sc and sc<0.3 else "큼" if sc and sc>=0.5 else "중간"),
      "subject_scale_auto": a["subject_scale"],
      "single_or_multi": v[1] if v else "미검증",
      "swing_visible": v[3] if v else "미검증",
      "bat_visible": v[4] if v else "미검증",
      "ball_visible": v[5] if v else "미검증",
      "pose_quality": f"det{p['person_ratio']}/arm{p['valid_arm_ratio']}/leg{p['valid_leg_ratio']}",
      "gate_arm_side": "pass" if gate_arm else "fail",
      "gate_leg": "pass" if num(p["gate_leg"]) is not None else "fail",
      "switch_frac": a["switch_frac"],
      "rot_peak": p["rp_peak_frame"], "rot_pos": p["rp_peak_pos"], "rot_npeaks": p["rp_n_peaks"],
      "peak_verdict": v[6] if v else "미검증",
      "bat_track": p["obj_baseball_bat"] or "",
      "usable_for_phase_B": "",
      "notes": v[7] if v else "",
    }
    # Phase B 사용 가능 판정: 팔 게이트 통과 + 피사체 안정 + 육안 miss/unusable 아님
    stable = (num(a["switch_frac"]) or 0) <= 0.05
    verdict = row["peak_verdict"]
    row["usable_for_phase_B"] = (
        "no" if verdict in ("miss","unusable") else
        "yes" if (gate_arm and stable and verdict in ("hit","near")) else
        "maybe" if gate_arm and stable else "no")
    out.append(row)

with open(ROOT/"phaseA_metadata.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

from collections import Counter
print("=== usable_for_phase_B ===", Counter(r["usable_for_phase_B"] for r in out).most_common())
print("=== peak_verdict(20건 육안) ===", Counter(r["peak_verdict"] for r in out if r["peak_verdict"]!="미검증").most_common())
print("=== camera_angle(20건) ===", Counter(r["camera_angle"] for r in out if r["camera_angle"]!="미검증").most_common())
print("=== single/multi(20건) ===", Counter(r["single_or_multi"] for r in out if r["single_or_multi"]!="미검증").most_common())
print("=== swing_visible(20건) ===", Counter(r["swing_visible"] for r in out if r["swing_visible"]!="미검증").most_common())
print(f"\n표 {len(out)}행 -> phaseA_metadata.csv")
