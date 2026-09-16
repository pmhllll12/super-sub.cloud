"""근거 문장이 **단위를 지어내는가**를 잰다 (미결 `ho` 43번 ㉱ 2회차).

판정 기준은 [`PREREGISTRATION_2.md`](PREREGISTRATION_2.md) 에 **돌리기 전에**
굳혔다.

    uv run python eval/pending43_evidence_plain/measure_units.py --out <csv>

🔴 **`src/` 를 고치지 않는다.** production 을 import 만 해서 문장을 만들고,
그 문장에 단위가 어떻게 나오는지 센다. 처방(프롬프트에 참인 단위 붙이기)은
이 스크립트가 아니라 `judge.build_prompt` 쪽에서 하고, 여기서는 **앞뒤를 같은
자로** 잰다.

🔴 **값을 등급마다 고정한다.** 매번 다른 값을 넣으면 앞뒤 비교가 흔들린다.
앵커에 적힌 값과 겹치지 않게 고른다 — 앵커를 그대로 베낀 문장을 「모델이 쓴
값」으로 세지 않기 위해서다.

## 🔴 사전 등록한 표본 설계를 고쳤다 (2026.09.16, **처방 전에**)

`PREREGISTRATION_2.md` 는 「루브릭 2 × 등급 3 × **5회 생성**」으로 적었는데
**첫 실행에서 계기 결함 둘이 드러났다.** 둘 다 결과가 아니라 **재는 방법**의
문제라, 처방을 넣기 전에 고치고 **앞뒤를 같은 새 설계로** 다시 잰다.

| 결함 | 무엇이 문제인가 | 고친 것 |
|---|---|---|
| **반복이 비어 있다** | 판정 경로가 **결정론적**이라(greedy) 5회가 **글자 하나까지 같았다**. 표본 30 이 아니라 **6** 이었다 | 반복 대신 **입력을 바꾼다**. 프레임 값 넷(3·7·12·20)을 돌려 분모를 늘린다 |
| **등급 입력이 루브릭마다 다르다** | 밴드가 달라서(인스텝 30↑ · 인사이드 8~25) 한 세트를 두 루브릭에 못 쓴다 — 두 번째 루브릭에서 멈췄다 | 각 루브릭의 **자기 밴드에서** 값을 고른다 |

**결정론은 그 자체로 기록한다** — 같은 입력을 두 번 돌려 같은지 확인하는
한 줄을 넣었다(기준 A 의 계기 검사).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.judge import Judge  # noqa: E402
from supersub_agent.scoring import load_rubric  # noqa: E402

#: 재는 항목. 지속 시간(프레임 값)을 `measured_by` 에 가진 유일한 항목이다.
CRITERION_ID = "follow_through"

#: 프레임 값 — 이 열을 돌린다. 🔴 앵커에 적힌 값(9·5·2 · 8·4·1)과 겹치지
#: 않게 골랐다: 앵커를 그대로 베낀 문장을 「모델이 쓴 값」으로 세지 않는다.
#:
#: 🔴 **넷에서 열로 늘렸다 (2026.09.16, 처방 전에).** 넷일 때 분모(값을 언급한
#: 문장)가 **3** 이었고, 사전 등록이 「분모 10 미만이면 판정하지 않고 표본을
#: 늘린다」고 적어 두었다. 모델이 지속 시간을 언급하는 비율 자체가 낮아서
#: (24문장 중 3) **문장 수를 늘리는 것 말고는 분모를 못 늘린다.**
FRAME_VALUES = (3, 6, 7, 11, 12, 13, 14, 17, 19, 20)

#: 밴드 안의 두 점 — 같은 등급에서 값만 다른 문장을 얻는다. 표본이 두 배가
#: 되고, 등급이 아니라 **값**에 반응하는지도 함께 보인다.
BAND_FRACTIONS = (0.35, 0.65)


def band_value(criterion, grade: int, frac: float = 0.5) -> float:
    """그 루브릭의 **자기 밴드** 안에서 등급 하나를 확실히 내는 값.

    밴드가 루브릭마다 다르다(인스텝 30도↑ 가 2등급 · 인사이드는 8~25도가
    2등급이고 25도 초과는 오히려 1등급이다). 한 세트를 두 루브릭에 쓰면
    엉뚱한 등급이 나온다 — 첫 실행이 거기서 멈췄다.
    """
    spans = criterion.bands[grade]
    lo, hi = spans[0]
    if lo is None:
        return round(float(hi) * frac, 1)
    if hi is None:
        return round(float(lo) + 2.0 + 8.0 * frac, 1)
    return round(float(lo) + (float(hi) - float(lo)) * frac, 1)


def _num(values: tuple[int, ...]) -> str:
    return "|".join(str(v) for v in values)


# 🔴 **계기를 두 번 고쳤다 (2026.09.16, 처방 전에)** — 첫 판은 세야 할 것을
#    못 세고 세지 말아야 할 것을 셌다. 사전 등록이 「분모를 먼저 못박는다」고
#    적었는데, **못박은 것은 분모의 정의였지 그것을 재는 자가 아니었다.**
#
#    ⑴ **분자가 0 을 냈다.** 「3초로」의 `로` 가 한글이라
#       `(?![가-힣])` 에 걸려 빠졌다 — 「초반」을 피하려던 조건이 **조사가 붙은
#       정상 표기를 전부 지웠다.** 이제 **조사·구두점이 이어지는 것만** 센다.
#    ⑵ **분모가 부풀었다.** `7.5도` 의 `7` 이 「지속 시간 7 을 언급」으로 잡혔다.
#       소수점 앞자리는 값이 아니다 — 앞뒤로 숫자·점이 없을 때만 센다.
_TAIL = r"(?=[로은는이가와과의도만,.\s)]|$)"

#: 문장이 **지속 시간 값을 언급했는가** (분모). 값 없이 「마무리가 짧다」고만
#: 한 문장은 단위를 붙일 자리가 없으므로 분모에서 뺀다.
MENTION = re.compile(rf"(?<![\d.])({_num(FRAME_VALUES)})(?![\d.])")

#: 🔴 분자 — 프레임 값 **바로 뒤**에 시간 단위를 붙인 경우.
TIME_UNIT = re.compile(rf"(?<![\d.])({_num(FRAME_VALUES)})\s*(초|분)" + _TAIL)

#: 짝 기준(D) — 프레임 값에 **각도·퍼센트**를 붙이는 새 거짓말.
WRONG_UNIT = re.compile(rf"(?<![\d.])({_num(FRAME_VALUES)})\s*(도|%)" + _TAIL)

#: 참인 표기 — 처방이 노린 것. 줄어든 거짓말이 **침묵**으로 간 것인지
#: **참인 말**로 간 것인지 갈라 준다(그 둘은 다르다).
TRUE_UNIT = re.compile(rf"(?<![\d.])({_num(FRAME_VALUES)})\s*프레임")


#: 🔴 **계기 자가검사** — 세야 할 것을 세고 세지 말아야 할 것을 안 세는가.
#: 위 두 결함이 각각 여기 한 줄씩으로 남아 있다(3·7 줄). 판정 전에 돌린다.
INSTRUMENT_CASES = [
    ("팔로스루 지속 시간은 3초로 짧습니다.", True, True),
    ("팔로스루 지속 시간은 20초로 비교적 짧은 편입니다.", True, True),
    ("지속 시간은 12로 비교적 안정적입니다.", True, False),
    ("임팩트 후 주동 고관절 굴곡 7.5도로 추가 각도 부족", False, False),
    ("경기 초반에 12프레임 동안 이어졌다", True, False),
    ("마무리가 짧다", False, False),
]


def check_instrument() -> None:
    for text, mention, time_unit in INSTRUMENT_CASES:
        assert bool(MENTION.search(text)) is mention, f"분모가 틀렸다: {text}"
        assert bool(TIME_UNIT.search(text)) is time_unit, f"분자가 틀렸다: {text}"


def measure(rubrics: list[Path], out: Path) -> None:
    check_instrument()
    judge = Judge()
    judge.load()
    rows = []
    twice: list[str] = []
    try:
        for rubric_path in rubrics:
            rubric = load_rubric(rubric_path)
            criterion = next(c for c in rubric.criteria if c.id == CRITERION_ID)
            for grade in (2, 1, 0):
              for frac in BAND_FRACTIONS:
                for frames in FRAME_VALUES:
                    features = {
                        "swing_hip_flexion_after_impact_deg":
                            band_value(criterion, grade, frac),
                        "follow_through_duration_frames": frames,
                    }
                    assert criterion.grade_for(features) == grade, (
                        f"{rubric_path.stem} {grade}등급 입력이 그 등급을 안 낸다 — "
                        "밴드가 바뀌었으면 band_value 를 다시 본다"
                    )
                    text = judge.judge_criterion(
                        criterion, features, rubric.sport).get("evidence", "")
                    rows.append({
                        "rubric": rubric_path.stem,
                        "grade": grade,
                        "frames": frames,
                        "deg": features["swing_hip_flexion_after_impact_deg"],
                        "mentions_value": bool(MENTION.search(text)),
                        "time_unit": bool(TIME_UNIT.search(text)),
                        "wrong_unit": bool(WRONG_UNIT.search(text)),
                        "true_unit": bool(TRUE_UNIT.search(text)),
                        "evidence": text,
                    })
                    print(f"[{rubric_path.stem} g{grade} {frames}f] {text}", flush=True)
                    # 🔴 계기 검사 — 같은 입력이 같은 문장을 내는가. 결정론이면
                    #    「반복」은 표본을 안 늘린다(사전 등록이 그렇게 적었다).
                    if not twice:
                        twice = [text, judge.judge_criterion(
                            criterion, features, rubric.sport).get("evidence", "")]
    finally:
        judge.unload()

    print(f"\n[계기 검사] 같은 입력 두 번이 같은 문장인가: "
          f"{'예 — 결정론적이다' if twice[0] == twice[1] else '🔴 아니다'}")

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    denom = sum(r["mentions_value"] for r in rows)
    print(f"\n문장 {len(rows)}개 · 값을 언급한 것 {denom}개(분모)")
    print(f"  🔴 시간 단위(초·분)를 붙인 것: {sum(r['time_unit'] for r in rows)}")
    print(f"  🔴 다른 단위(도·%)를 붙인 것: {sum(r['wrong_unit'] for r in rows)}")
    print(f"  ✅ 참인 단위(프레임)를 붙인 것: {sum(r['true_unit'] for r in rows)}")
    print(f"→ {out}")
    if denom < 10:
        print("🔴 분모가 10 미만이다 — 사전 등록 기준 A 대로 판정하지 않는다")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--rubrics", nargs="*", type=Path, default=[
        ROOT / "rubrics" / "football_instep_shot.yaml",
        ROOT / "rubrics" / "football_inside_pass.yaml",
    ])
    args = ap.parse_args()
    measure(args.rubrics, args.out)


if __name__ == "__main__":
    main()
