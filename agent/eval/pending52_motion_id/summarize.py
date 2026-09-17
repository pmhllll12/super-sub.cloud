"""`motion_raw.json` → 사전 등록한 합격 기준 A~E 표 (미결 `ho` 52번 1회차).

🔴 **기준은 `PREREGISTRATION.md` 에 있다. 여기서 고치지 않는다.**

    cd agent && uv run python eval/pending52_motion_id/summarize.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 사전 등록한 합격선.
A_MIN_ACC = 0.80
B_MAX_UNKNOWN = 0.30
C_MAX_SHOT_AS_PASS = 0.10
E_MIN_PER_CLASS = 15
SUBJECT_FAIL_DIST = 1.2

TRUE = {"inside_pass": "pass", "instep_shot": "shot"}


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def main() -> int:
    rows = json.loads((HERE / "motion_raw.json").read_text(encoding="utf-8"))

    errored = [r for r in rows if r.get("error")]
    ok = [r for r in rows if not r.get("error")]

    # 🔴 계기 검사 — 공이 발에서 멀면 분류 실패가 아니라 **대상 선택 실패**다.
    subject_fail = [r for r in ok
                    if r.get("foot_ball") is not None
                    and r["foot_ball"] > SUBJECT_FAIL_DIST]
    failed_ids = {id(r) for r in subject_fail}
    judged = [r for r in ok if id(r) not in failed_ids]

    print("## 표본")
    print(f"- 측정 시도 {len(rows)}편 · 포즈/구간 실패 {len(errored)}편")
    print(f"- 🔴 대상 선택 실패(공-발 > {SUBJECT_FAIL_DIST} 어깨너비) {len(subject_fail)}편 — 판정에서 뺀다")
    print(f"- 판정 대상 {len(judged)}편")
    for label in ("inside_pass", "instep_shot"):
        n = sum(1 for r in judged if r["label"] == label)
        print(f"  - {label}: {n}편")
    if errored:
        print("\n실패 사유:")
        for r in errored:
            print(f"  - {r['clip'][:20]:22s} {r['error'][:70]}")

    decided = [r for r in judged if r["pred"] != "unknown"]
    unknown = [r for r in judged if r["pred"] == "unknown"]
    correct = [r for r in decided if r["pred"] == TRUE[r["label"]]]

    shots = [r for r in judged if r["label"] == "instep_shot"]
    shot_as_pass = [r for r in shots if r["pred"] == "pass"]

    acc = len(correct) / len(decided) if decided else None
    unk = len(unknown) / len(judged) if judged else None
    sap = len(shot_as_pass) / len(shots) if shots else None
    per_class_ok = all(
        sum(1 for r in judged if r["label"] == lb) >= E_MIN_PER_CLASS
        for lb in ("inside_pass", "instep_shot"))

    print("\n## 판정")
    print("| | 기준 | 결과 | |")
    print("|---|---|---|---|")
    print(f"| **A** | 일치율 ≥ {A_MIN_ACC:.0%} | "
          f"{fmt(acc) if acc is None else f'{acc:.0%} ({len(correct)}/{len(decided)})'} | "
          f"{'✅' if acc is not None and acc >= A_MIN_ACC else '🔴'} |")
    print(f"| **B** | unknown ≤ {B_MAX_UNKNOWN:.0%} | "
          f"{unk:.0%} ({len(unknown)}/{len(judged)}) | "
          f"{'✅' if unk is not None and unk <= B_MAX_UNKNOWN else '🔴'} |")
    print(f"| **C** | 슛→패스 ≤ {C_MAX_SHOT_AS_PASS:.0%} | "
          f"{sap:.0%} ({len(shot_as_pass)}/{len(shots)}) | "
          f"{'✅' if sap is not None and sap <= C_MAX_SHOT_AS_PASS else '🔴'} |")
    print("| **D** | production 무수정 | import 만 했다 | ✅ |")
    print(f"| **E** | 두 층 각 ≥ {E_MIN_PER_CLASS}편 | "
          f"{'충족' if per_class_ok else '미달'} | {'✅' if per_class_ok else '🔴'} |")

    print("\n## 혼동표 (판정 대상)")
    print("| 실제 \\ 예측 | pass | shot | unknown |")
    print("|---|---:|---:|---:|")
    for label in ("inside_pass", "instep_shot"):
        sub = [r for r in judged if r["label"] == label]
        row = [sum(1 for r in sub if r["pred"] == p) for p in ("pass", "shot", "unknown")]
        print(f"| {label} | {row[0]} | {row[1]} | {row[2]} |")

    print("\n## 신호별 — 무엇이 갈랐나")
    print("| 신호 | 던진 표 | 맞은 표 | 기권·측정불가 |")
    print("|---|---:|---:|---:|")
    for s in ("S1", "S2", "S3", "S4"):
        cast = [r for r in judged if r["votes"].get(s) in ("shot", "pass")]
        hit = [r for r in cast if r["votes"][s] == TRUE[r["label"]]]
        idle = len(judged) - len(cast)
        rate = f"{len(hit)}/{len(cast)} ({len(hit)/len(cast):.0%})" if cast else "—"
        print(f"| {s} | {len(cast)} | {rate} | {idle} |")

    print("\n## 값의 분포 (판정 대상)")
    print("| 지표 | 인사이드 패스 중앙값 | 인스텝 슛 중앙값 | 겹치나 |")
    print("|---|---:|---:|---|")
    for key in ("ball_speed", "ball_rise", "follow_through", "knee_ang_vel"):
        vals = {}
        for label in ("inside_pass", "instep_shot"):
            v = [r[key] for r in judged
                 if r["label"] == label and r.get(key) is not None]
            vals[label] = (statistics.median(v), min(v), max(v)) if v else None
        p, s = vals["inside_pass"], vals["instep_shot"]
        if p and s:
            overlap = not (p[2] < s[1] or s[2] < p[1])
            print(f"| `{key}` | {p[0]:.1f} [{p[1]:.1f}, {p[2]:.1f}] | "
                  f"{s[0]:.1f} [{s[1]:.1f}, {s[2]:.1f}] | "
                  f"{'겹친다' if overlap else '**안 겹친다**'} |")
        else:
            print(f"| `{key}` | {'—' if not p else p[0]} | {'—' if not s else s[0]} | — |")

    print("\n## 계기 검사 — 공 검출")
    covs = [r["ball_coverage"] for r in ok if r.get("ball_coverage") is not None]
    if covs:
        print(f"- 공 검출 커버리지 중앙값 **{statistics.median(covs):.0%}** "
              f"(최소 {min(covs):.0%} · 최대 {max(covs):.0%})")
    if subject_fail:
        print(f"- 🔴 대상 선택 실패 {len(subject_fail)}편의 공-발 거리: "
              + " · ".join(f"{r['foot_ball']:.2f}" for r in
                           sorted(subject_fail, key=lambda r: r["foot_ball"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
