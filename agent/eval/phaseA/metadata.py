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
 # 🔴 정정 (2026.09.03). 옛 판독은 "신발 클로즈업. 타자가 피사체가 아님"이었는데
 # **틀렸다** — 스켈레톤이 붙은 사람이 타자가 맞고, 신발은 앞에 있던 다른 사람이
 # 찍힌 것이다. 미결 6번 판독(side_form.csv)에서 subject_ok=y 로 확인됐다.
 # 그 오진에 딸려 있던 두 칸을 `None`으로 비워 **자동 산출로 되돌린다**:
 #   player_scale "해당없음"  — 대상이 없다는 전제로 매긴 값이다. 대상이 있으므로
 #                              subject_scale=0.568 에 나머지 19클립과 같은 규칙이
 #                              적용된다 (>=0.5 → "큼")
 #   peak_verdict "unusable"  — 이 표의 범례가 "대상 자체를 못 봄"이라고 정의한다.
 #                              전제가 무너졌고 peak 위치는 다시 보지 않았으므로
 #                              "미검증"으로 돌아간다
 # 손으로 새 값을 적어 넣지 않는 이유는 **출처를 지키기 위해서다** — 그러면 그
 # 칸이 판독인지 산출인지 알 수 없게 된다.
 # `single_or_multi = 단일`은 손대지 않는다 — 앞사람의 신발만 걸렸을 수 있어
 # "다인"이라고 단정할 근거가 아직 없다. 다시 볼 때 함께 확인할 것.
 # `usable_for_phase_B`(파생값)는 no 그대로다 — bat 가림·ball 미검출이라는
 # 별개 사유가 남아 있고, 그것까지 이 정정으로 뒤집을 근거는 없다.
 "w-AQcjcoDyA": ("측면","단일",None,"불명","가림","미검출",None,
                 "타자가 피사체가 맞다(2026.09.03 정정). 앞사람 신발이 함께 잡힘 — "
                 "옛 판독 '타자가 피사체가 아님'은 오진이었다"),
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
      # 육안 판독이 `None`을 두면 **자동 산출로 되돌린다.** 판독이 틀린 것으로
      # 밝혀졌을 때 손으로 값을 새로 적어 넣으면 그 값의 출처를 알 수 없게 되므로,
      # 나머지 19클립과 같은 규칙이 다시 적용되게 한다 (w-AQcjcoDyA 참고).
      "player_scale": (v[2] if v and v[2] else
                       ("작음" if sc and sc<0.3 else "큼" if sc and sc>=0.5 else "중간")),
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
      "peak_verdict": v[6] if v and v[6] else "미검증",
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
