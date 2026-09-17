#!/usr/bin/env python3
"""임계값 검수 서식을 만든다 — 지도자에게 내밀 종이 (미결 2번 (A)).

    uv run python eval/pending2_bands/build_review_packet.py            # 미리보기
    uv run python eval/pending2_bands/build_review_packet.py --write    # 파일로

**무엇을 푸는가.** 미결 2번의 (A) 임계값 검수는 「지도자 1명이면 되고 적은
수로 지금 시작할 수 있다」고 정리됐고 박민호 님이 섭외 계획까지 세우셨다.
🔴 **그런데 지도자가 와도 내밀 것이 없었다.** 이 스크립트가 그것을 만든다.

**(A)는 클립을 보고 매기는 일이 아니다.** 그것은 (B) 정답 라벨이고 표본 수가
안 차면 무의미하다. (A)는 **실측 분포를 놓고 「이 구간이 맞습니까」를 묻는
자리**다 — 클립을 한 편도 안 봐도 답할 수 있고, 그래서 한 시간이면 끝난다.

항목마다 이렇게 묻는다.

    · 무엇을 재는가 (사람 말로, 단위와 함께)
    · 지금 구간은 이렇다 (2/1/0 등급)
    · 우리 클립에서 실제로 나온 값은 이렇게 퍼져 있다 (최소~최대·사분위)
    · 그 구간이 실제로 낸 등급은 이렇다 (2/1/0 몇 편)
    · **여기서 갈라야 합니까? 어디로 옮겨야 합니까?**  ← 지도자가 채우는 칸

🔴 **숫자를 지어내지 않는다.** 분포는 이미 있는 실측에서만 온다 — 포즈를
다시 뽑지 않는다. 표본이 없는 루브릭은 **없다고 적고 넘어간다**(빈 칸을
그럴듯한 값으로 채우면 그 값으로 구간이 정해진다).

🔴 **처방을 미리 적지 않는다.** 지금 구간이 이상해 보여도 이 서식은 그것을
지적하지 않는다 — 유도하면 검수가 아니라 확인이 된다. 미결 20·22번이 찾은
결함도 여기 안 적는다(그건 결과를 받은 뒤에 대조할 것이다).
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import discover_rubrics  # noqa: E402

TRACK2 = ROOT / "eval" / "phaseA" / "eval_b6" / "selector_downstream_rubric_clips.csv"
BATTING = ROOT / "eval" / "jhmdb_batting" / "features_swing_baseball.json"
OUT_DIR = Path(__file__).resolve().parent / "packet"

# `measure_ceiling.py` 와 같은 자료를 같은 방식으로 읽는다. 두 곳이 다른
# 표본을 쓰면 같은 항목의 수치가 문서마다 달라진다.
METRIC_COLS = (
    "plant_knee_angle_at_impact", "swing_knee_angle_at_impact",
    "trunk_forward_lean_deg_at_impact", "hip_rotation_range_deg",
    "swing_hip_flexion_after_impact_deg", "follow_through_duration_frames",
    "swing_elbow_angle_at_impact", "support_elbow_angle_at_impact",
    "swing_shoulder_flexion_after_impact_deg", "hip_shoulder_separation_deg",
)

UNIT_WORD = {"deg": "도", "s": "초", "ratio": "배(어깨너비 기준)", "score": "점"}


def metric_labels() -> dict[str, tuple[str, str]]:
    """지표 코드 → (사람이 읽을 이름, 단위 낱말). 정본은 contracts/ 다."""
    import yaml

    path = ROOT / "contracts" / "metric_definitions.yaml"
    defs = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {m["code"]: (m["label"], UNIT_WORD.get(m["unit"], m["unit"]))
            for m in defs["metrics"]}


def load_samples() -> list[tuple[str, object, list[dict]]]:
    """🔴 **루브릭 전체를 돈다.** 표본 목록을 손으로 적으면 거기 없는 루브릭이
    조용히 빠진다 — 실제로 첫 판에서 축구 인사이드 패스가 빠졌고, 서식이
    5개만 나온 것을 세어 보고서야 알았다. 표본이 없는 것은 **없다고 적는다.**
    """
    batting_data = json.loads(BATTING.read_text(encoding="utf-8"))
    batting = [x["features"] for x in batting_data["records"] if "features" in x]

    with open(TRACK2, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["comparison_selector"] == "baseline" and r["features_ok"] == "1"]

    jobs: list[tuple[str, object, list[dict]]] = []
    for key, rubric in sorted(discover_rubrics(ROOT / "rubrics").items()):
        if key == "baseball/batting":
            jobs.append((f"JHMDB {len(batting)}편", rubric, batting))
            continue
        samples = [
            {m: float(r[m]) for m in METRIC_COLS if r[m].strip()}
            for r in rows if r["rubric"] == key
        ]
        jobs.append((f"B-6 Track2 {len(samples)}편", rubric, samples))
    return jobs


def spread(values: list[float]) -> str:
    """분포 한 줄. 🔴 표본이 적으면 사분위를 내지 않는다 — 없는 정밀도다."""
    n = len(values)
    if n == 0:
        return "**측정된 값이 없습니다**"
    lo, hi = min(values), max(values)
    med = statistics.median(values)
    if n < 8:
        return f"{n}편 · {lo:.0f} ~ {hi:.0f} (가운데 {med:.0f})"
    q = statistics.quantiles(values, n=4)
    return (f"{n}편 · {lo:.0f} ~ {hi:.0f} · "
            f"가운데 절반이 **{q[0]:.0f} ~ {q[2]:.0f}** (중앙 {med:.0f})")


def grade_tally(criterion, samples: list[dict]) -> str:
    counts = {0: 0, 1: 0, 2: 0}
    for f in samples:
        if criterion.is_applicable(f):
            counts[criterion.grade_for(f)] += 1
        # 못 잰 것은 세지 않는다 — 0등급이 아니라 제외다.
    total = sum(counts.values())
    if not total:
        return "—"
    return (f"잘함 {counts[2]} · 보통 {counts[1]} · 아쉬움 {counts[0]}"
            f"  (판정된 {total}편)")


def render(rubric, sample_label: str, samples: list[dict],
           labels: dict[str, tuple[str, str]]) -> str:
    out: list[str] = []
    a = out.append
    a(f"# 임계값 검수 — {rubric.label}")
    a("")
    a(f"루브릭 {rubric.version} · 표본 {sample_label} · 항목 {len(rubric.criteria)}개")
    a("")
    a("## 먼저 읽어 주세요")
    a("")
    a("저희는 영상에서 **각도와 거리를 자동으로 잽니다.** 그 숫자를 어디서 끊어")
    a("「잘함 / 보통 / 아쉬움」으로 볼지가 **지금은 저희가 임시로 정한 값**입니다.")
    a("그 선이 맞는지를 여쭙는 자리입니다.")
    a("")
    a("- **클립을 보실 필요는 없습니다.** 숫자만 보고 답하실 수 있게 만들었습니다")
    a("- 「우리 클립에서 나온 값」은 실제로 측정된 분포입니다. 이 종목 선수들이")
    a("  **실제로 어디쯤에 몰려 있는지**를 참고하시라고 함께 적었습니다")
    a("- 🔴 **분포에 맞춰 선을 그으실 필요는 없습니다.** 저희 표본이 잘하는")
    a("  선수들이 아닐 수 있습니다. 「이 종목에서 이 정도면 잘한 것이다」를")
    a("  적어 주시면 됩니다")
    a("- 모르시겠거나 이 항목이 무의미해 보이면 **그렇게 적어 주세요.**")
    a("  「이 항목은 빼야 한다」도 저희에게는 답입니다")
    a("")

    for i, c in enumerate(rubric.criteria, 1):
        values = [f[c.band_metric] for f in samples if c.band_metric in f]
        label, unit = labels.get(c.band_metric, (c.band_metric, ""))
        a("---")
        a("")
        a(f"## {i}. {c.name}")
        a("")
        if c.rationale:
            a(f"> {c.rationale.strip()}")
            a("")
        a(f"**재는 것**: {label} (단위: {unit})")
        a("")
        a("| | 지금 선 |")
        a("|---|---|")
        for g, word in ((2, "잘함"), (1, "보통"), (0, "아쉬움")):
            a(f"| {word} | {c.band_text(g) or '나머지 전부'} |")
        a("")
        a(f"**우리 클립에서 나온 값**: {spread(values)}")
        a("")
        a(f"**지금 선이 낸 결과**: {grade_tally(c, samples)}")
        a("")
        a("### 여쭙습니다")
        a("")
        a("| | 적어 주세요 |")
        a("|---|---|")
        a("| 이 선이 맞습니까? | ☐ 맞다   ☐ 고쳐야 한다   ☐ 모르겠다 |")
        a("| 고쳐야 한다면, **잘함**은 어디부터 어디까지입니까? | |")
        a("| **아쉬움**은 어디부터입니까? | |")
        a("| 이 항목 자체에 대해 하실 말씀 | |")
        a("")

    a("---")
    a("")
    a("## 마지막으로")
    a("")
    a("| | 적어 주세요 |")
    a("|---|---|")
    a("| 이 종목에서 **빠진 항목**이 있습니까? | |")
    a("| 위 항목 중 **중요도가 다른 것**이 있습니까? (지금은 항목마다 비중이 다릅니다) | |")
    a("| 검수에 걸린 시간 | 분 |")
    a("")
    a(f"검수자: ____________  날짜: ____________  종목·동작: {rubric.label}")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help=f"{OUT_DIR} 에 파일로 쓴다")
    ap.add_argument("--only-active", action="store_true",
                    help="열려 있는 루브릭만 (기본은 draft 도 낸다)")
    args = ap.parse_args()

    labels = metric_labels()
    jobs = load_samples()
    if args.only_active:
        jobs = [j for j in jobs if j[1].is_active]

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sample_label, rubric, samples in jobs:
        text = render(rubric, sample_label, samples, labels)
        if args.write:
            path = OUT_DIR / f"{rubric.sport}_{rubric.motion}.md"
            path.write_text(text, encoding="utf-8")
            missing = sum(1 for c in rubric.criteria
                          if not any(c.band_metric in f for f in samples))
            note = f" · 🔴 표본 없는 항목 {missing}개" if missing else ""
            print(f"{path.relative_to(ROOT)}  ({rubric.status}, {sample_label}{note})")
        else:
            print(text)


if __name__ == "__main__":
    main()
