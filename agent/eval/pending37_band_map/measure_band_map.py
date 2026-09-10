#!/usr/bin/env python3
"""밴드 반전 **지도** — 표본 없이 구조를 전수로 (미결 `ho` 37번 2회차).

    uv run python eval/pending37_band_map/measure_band_map.py    # GPU 불필요

1회차(`eval/pending37_trunk_mirror/`)가 **크기**를 쟀다: 축구 인스텝 18클립에서
최종 등급 44% 변동. 그런데 **가장 위험한 두 루브릭(투구·인사이드 패스)은
표본이 0** 이라 못 쟀다.

🔴 **그 표본은 지금 데이터로 못 채운다** — 투구 클립은 이미 품질로 탈락한 그
하나뿐이고, 축구 골든셋 19편은 전부 penalty/freekick(**인스텝**)이다.

그래서 질문을 **둘로 가른다**:

    구조 (밴드가 어떻게 생겼나)  → 표본 없이 **전수**로 답할 수 있다  ← 이 회차
    분포 (실측 θ 가 어디 떨어지나) → 그 두 루브릭에서는 **못 답한다**

이 회차는 정의역 전체에서 `g(θ)` 와 `g(-θ)` 를 비교한다. 🔴 **분포를 답한
척하지 않는다.**

규격은 `PREREGISTRATION.md`(커밋 `6a99669`, 코드보다 먼저).

🔴 **`features.py`·`rubrics/`·앞 회차 스크립트를 고치지 않는다.** import 만 한다.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.features import PLAUSIBLE_RANGE  # noqa: E402
from supersub_agent.scoring import Criterion, Rubric, load_rubric  # noqa: E402

METRIC = "trunk_forward_lean_deg_at_impact"

# 🔴 정의역은 **`features.py` 의 선언 그대로**다 — 내가 고른 범위가 아니다.
LO, HI = PLAUSIBLE_RANGE[METRIC]
STEP = 0.1          # 밴드 경계가 전부 정수라 0.1도면 놓치지 않는다

RUBRIC_FILE = {
    "baseball/pitching": "baseball_pitching.yaml",
    "football/inside_pass": "football_inside_pass.yaml",
    "football/instep_shot": "football_instep_shot.yaml",
    "basketball/jump_shot": "basketball_jump_shot.yaml",
    "basketball/layup": "basketball_layup.yaml",
    "baseball/batting": "baseball_batting.yaml",
}
# 1회차가 실측을 낸 것 — 「구조」와 「분포」를 함께 볼 수 있는 둘.
HAS_SAMPLE = ("football/instep_shot", "baseball/batting",
              "basketball/jump_shot", "basketball/layup")

TRACK2 = ROOT / "eval" / "phaseA" / "eval_b6" / "selector_downstream_rubric_clips.csv"
BATTING = ROOT / "eval" / "jhmdb_batting" / "features_swing_baseball.json"


def trunk_criterion(rubric: Rubric) -> Criterion | None:
    for c in rubric.criteria:
        if c.band_metric == METRIC:
            return c
    return None


def grid():
    n = int(round((HI - LO) / STEP))
    return [round(LO + i * STEP, 1) for i in range(n + 1)]


def flip_map(c: Criterion):
    """정의역 전수에서 (θ, g(θ), g(-θ)). production 경로로 등급을 낸다."""
    out = []
    for t in grid():
        try:
            a = c.grade_for({METRIC: t})
            b = c.grade_for({METRIC: -t})
        except Exception:
            continue
        out.append((t, a, b))
    return out


def intervals(rows, pred):
    """조건을 만족하는 연속 구간을 [(시작, 끝), ...] 로 접는다."""
    spans, start, prev = [], None, None
    for t, a, b in rows:
        if pred(a, b):
            if start is None:
                start = t
            prev = t
        else:
            if start is not None:
                spans.append((start, prev))
                start = None
    if start is not None:
        spans.append((start, prev))
    return spans


def fmt_spans(spans, limit=3):
    if not spans:
        return "없다"
    txt = " · ".join(f"[{a:g}, {b:g}]" for a, b in spans[:limit])
    return txt + (f" 외 {len(spans) - limit}개" if len(spans) > limit else "")


def observed():
    """1회차와 **같은 규칙**으로 실측 θ 를 읽는다 (기준 C 대조용)."""
    by = {}
    for r in csv.DictReader(TRACK2.open(encoding="utf-8")):
        if r.get("comparison_selector", "").strip() != "baseline":
            continue
        if r.get("features_ok", "").strip().lower() not in ("true", "1", "yes"):
            continue
        v = (r.get(METRIC) or "").strip()
        if v in ("", "None", "nan"):
            continue
        by.setdefault(r["rubric"], []).append(float(v))
    d = json.loads(BATTING.read_text(encoding="utf-8"))
    for rec in d["records"]:
        f = rec.get("features") or {}
        if METRIC in f:
            by.setdefault("baseball/batting", []).append(float(f[METRIC]))
    return by


def main() -> None:
    rubrics = {k: load_rubric(ROOT / "rubrics" / v) for k, v in RUBRIC_FILE.items()}
    obs = observed()

    print("═" * 100)
    print(f"밴드 반전 지도 — 정의역 [{LO:g}, {HI:g}] (features.py `PLAUSIBLE_RANGE` 그대로) · "
          f"격자 {STEP}도")
    print("═" * 100)
    print(f"  {'루브릭':22s} {'w':>5s} │ {'뒤집힘':>7s} │ {'Δ=2':>7s} │ "
          f"{'0등급 하한':>10s} │ 표본")

    maps = {}
    for key, rubric in rubrics.items():
        c = trunk_criterion(rubric)
        if c is None:
            continue
        rows = flip_map(c)
        maps[key] = (c, rows)
        flip = [r for r in rows if r[1] != r[2]]
        two = [r for r in rows if abs(r[1] - r[2]) == 2]
        pct = len(flip) / len(rows) if rows else 0.0
        pct2 = len(two) / len(rows) if rows else 0.0
        # 0 등급이 되는 가장 큰 θ — 0 을 경계로 쓰는지 보이려고 낸다
        zero_below = max((t for t, a, _b in rows if a == 0 and t < 0), default=None)
        zb = f"{zero_below:g}" if zero_below is not None else "—"
        sample = f"{len(obs.get(key, []))}클립" if key in HAS_SAMPLE else "🔴 **0**"
        mark = " 🔴" if pct >= 0.5 else ""
        print(f"  {key:22s} {c.weight:5.2f} │ {pct:6.0%}{mark:2s} │ {pct2:6.0%} │ "
              f"{zb:>10s} │ {sample}")

    # --- 표본이 없는 둘을 자세히 ---------------------------------------
    print("\n" + "═" * 100)
    print("🔴 1회차가 못 잰 둘 — 표본이 0이라 **구조만** 답한다")
    print("═" * 100)
    for key in ("baseball/pitching", "football/inside_pass"):
        c, rows = maps[key]
        two = intervals(rows, lambda a, b: abs(a - b) == 2)
        one = intervals(rows, lambda a, b: abs(a - b) == 1)
        print(f"\n  ▸ {key}   (`{c.id}`, 가중치 {c.weight})")
        print(f"      2등급 차로 뒤집히는 θ : {fmt_spans(two)}")
        print(f"      1등급 차로 뒤집히는 θ : {fmt_spans(one)}")

    # --- 실측이 있는 둘: 구조와 분포를 같이 ------------------------------
    print("\n" + "═" * 100)
    print("실측이 있는 것 — 구조와 분포를 **같이** 본다")
    print("═" * 100)
    for key in ("football/instep_shot", "baseball/batting"):
        c, rows = maps[key]
        vals = obs.get(key, [])
        lookup = {t: (a, b) for t, a, b in rows}
        hit = sum(1 for v in vals
                  if lookup.get(round(v, 1), (0, 0))[0]
                  != lookup.get(round(v, 1), (0, 0))[1])
        flip_pct = sum(1 for r in rows if r[1] != r[2]) / len(rows)
        print(f"  {key:22s} 정의역 뒤집힘 {flip_pct:.0%} · "
              f"실측 {hit}/{len(vals)}클립이 그 구간에 있다")

    # --- 총점 환산 ------------------------------------------------------
    print("\n" + "═" * 100)
    print("총점 환산 — `score = Σ(wᵢ/Σw)·(gᵢ/2)·100` 이므로 Δg 뒤집힘은 "
          "`(w/Σw)·(Δg/2)·100` 점")
    print("═" * 100)
    print("  🔴 `Σw` 는 **적용된 항목**의 합이라, 도구 미검출로 항목이 빠지면 "
          "영향이 **커진다.**")
    print(f"  {'루브릭':22s} │ {'Δ=2 일 때 (전 항목 적용)':>24s} │ "
          f"{'한 항목 빠지면':>16s}")
    for key, (c, _rows) in maps.items():
        total = sum(x.weight for x in rubrics[key].criteria)
        full = c.weight / total * 100
        least = min((x.weight for x in rubrics[key].criteria if x.id != c.id),
                    default=0.0)
        drop = c.weight / (total - least) * 100 if total > least else full
        print(f"  {key:22s} │ {full:20.1f}점 │ {drop:12.1f}점")

    # --- 기준 -----------------------------------------------------------
    bat_rows = maps["baseball/batting"][1]
    a_ok = all(a == b for _t, a, b in bat_rows)
    b_ok = True   # grade_for 를 그대로 썼다 (밴드를 다시 구현하지 않았다)
    ins_c, ins_rows = maps["football/instep_shot"]
    ins_lookup = {t: (a, b) for t, a, b in ins_rows}
    ins_hit = sum(1 for v in obs.get("football/instep_shot", [])
                  if ins_lookup.get(round(v, 1), (0, 0))[0]
                  != ins_lookup.get(round(v, 1), (0, 0))[1])
    c_ok = ins_hit == len(obs.get("football/instep_shot", []))

    print("\n" + "═" * 100)
    print("사전 등록 기준 (커밋 `6a99669` — 결과를 보고 바꾸지 않았다)")
    print("═" * 100)
    print(f"  A 자기 검사 — 타격(대칭 밴드) 뒤집힘 0% …… "
          f"{'✅ 만족' if a_ok else '🔴 불만족'}")
    print(f"  B production `grade_for` 를 그대로 썼다 …… "
          f"{'✅ 만족' if b_ok else '🔴 불만족'}")
    print(f"  C 1회차 실측과 어긋나지 않는가 ……………… "
          f"{'✅ 만족' if c_ok else '🔴 불만족'}"
          f"   (인스텝 {ins_hit}/{len(obs.get('football/instep_shot', []))} — "
          "1회차가 센 18/18 과 같아야 한다)")
    print("  D `features.py`·`rubrics/` 미수정 …………… ✅ import 만 했다")

    print("\n" + "═" * 100)
    print("🔴 이 회차가 **못 말하는 것**")
    print("═" * 100)
    print("  정의역 비율은 「얼마나 자주 나는가」가 **아니다** — 실측 θ 가")
    print("  균등분포일 이유가 없다. 투구·인사이드 패스는 **구조만** 나왔고")
    print("  분포는 표본이 생겨야 안다. 그리고 여전히 **정답이 없어** 어느")
    print("  부호가 옳은지는 못 말한다.")


if __name__ == "__main__":
    main()
