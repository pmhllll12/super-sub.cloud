"""F 가 얻은 것은 **어디서** 왔나 — 자리의 성질로 가른다 (미결 23번 G).

    uv run python eval/pending23_evidence/order_source.py

사전 등록: `PREREGISTRATION_order_source.md`. 결과를 보고 이 스크립트를 고치지
않는다.

🔴 **관측 회차다.** 새 문장을 안 만들고 `src/` 도 안 고친다. 이미 있는
`evidence_other_levels.json`(C0, 등급 순) 과 `evidence_anchor_order.json`(F,
값 순) 을 읽어 **자리를 두 축으로** 가른다.

    ㉮ 양방향인가          — 판정 등급의 `bands[grade]` 구간이 둘 이상인가
    ㉯ 차례가 바뀌었는가   — 등급 내림차순 배열과 값 오름차순 배열이 다른가

**둘 다 코드로 판정되므로 판독이 안 들어간다.** 판독이 필요한 것(방향 오독)은
`reading_F.json` 의 판정을 **그대로 읽는다** — 다시 읽지 않는다(사전 등록 5절).

🔴 **㉯ 를 production 과 같은 방식으로 구한다.** `build_prompt` 가 고르는 앵커
집합(가-3: 옆 등급 전부 + 판정 등급은 값이 앉은 조각)을 그대로 쓴다 — 여기서
다르게 고르면 「차례가 바뀌었는가」가 실물과 어긋난다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import discover_rubrics  # noqa: E402

C0_FILE = "evidence_other_levels.json"
F_FILE = "evidence_anchor_order.json"

#: F 회차 판독(`reading_F.json`)이 낸 것. 🔴 **다시 읽지 않는다.**
FIXED = ["inside_pass/hip_rotation/85.8",
         "instep_shot/trunk_lean/1.8", "instep_shot/trunk_lean/23.5"]
WORSE = ["inside_pass/hip_rotation/129.2", "instep_shot/trunk_lean/26.5"]
#: E 가 무너뜨렸다가 F 에서 회복된 잘함 자리(`reading_E_grade2.json`).
RECOVERED = ["inside_pass/swing_knee_extension/132.2",
             "inside_pass/swing_knee_extension/142.8"]
#: `check_evidence.py --show` 가 C0 에서 짚은 R3 두 건. 🔴 **세기 전에 확인했다** —
#: 사전 등록에 자리를 안 적어 뒀기에 추측하지 않고 검사기에게 물었다.
#:
#: 🔴 두 번째를 처음에 `19.8` 로 적었다가 **못 찾았다.** 19.8 은 문장이
#: **지어낸 숫자**이고 그 자리에 실제로 준 값은 **21.5** 다 — R3 가 잡는 것이
#: 바로 그 어긋남이라, 지어낸 숫자로 자리를 찾으면 영영 안 나온다.
R3_C0 = ["inside_pass/follow_through/4.8", "instep_shot/hip_rotation/21.5"]


def shown_anchors(criterion, grade: int, value: float) -> tuple[dict, ...]:
    """`build_prompt` 가 실제로 싣는 앵커 집합 (가-3 규칙 그대로)."""
    return tuple(
        a for a in criterion.anchors if int(a.get("grade", -1)) != grade
    ) + criterion.anchors_for(grade, value)


def order_changed(criterion, grade: int, value: float) -> bool:
    """등급 내림차순과 값 오름차순이 **다른 차례**를 내는가."""
    shown = shown_anchors(criterion, grade, value)
    by_grade = [id(a) for a in sorted(shown, key=lambda a: -int(a.get("grade", 0)))]
    by_value = [id(a) for a in sorted(
        shown, key=lambda a: float(a["measured"][criterion.band_metric]))]
    return by_grade != by_value


def main() -> None:
    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    rows = {}
    for tag, name in (("C0", C0_FILE), ("F", F_FILE)):
        data = json.loads((HERE / name).read_text(encoding="utf-8"))
        for key, payload in data["clips"].items():
            for item in payload["items"]:
                criterion = rubrics[key].get(item["criterion_id"])
                grade = item["grade"]
                value = item["given_metrics"][criterion.band_metric]
                ident = f"{key.split('/')[-1]}/{criterion.id}/{value}"
                row = rows.setdefault(ident, {
                    "grade": grade,
                    "양방향": len(criterion.bands[grade]) > 1,
                    "차례바뀜": order_changed(criterion, grade, value),
                })
                row[tag] = item["evidence"]

    def cell(r):
        return ("양방향" if r["양방향"] else "한방향",
                "차례바뀜" if r["차례바뀜"] else "차례그대로")

    # --- P-1 (계기 검사) ---------------------------------------------------
    same_order = [i for i, r in rows.items() if not r["차례바뀜"]]
    broke = [i for i in same_order if rows[i]["C0"] != rows[i]["F"]]
    print(f"P-1 계기 검사 — 차례가 안 바뀐 자리 {len(same_order)}개 중 "
          f"문장이 바뀐 것 {len(broke)}개",
          "✅" if not broke else "🔴 대조가 깨졌다 — 중단할 것")
    for i in broke[:5]:
        print(f"    - {i}")

    # --- M4 -----------------------------------------------------------------
    print("\nM4 — 차례가 바뀐 자리에서만 문장이 바뀌는가")
    for changed_order in (True, False):
        grp = [r for r in rows.values() if r["차례바뀜"] is changed_order]
        ch = sum(1 for r in grp if r["C0"] != r["F"])
        label = "차례바뀜" if changed_order else "차례그대로"
        pct = f"{ch / len(grp):.0%}" if grp else "—"
        print(f"  {label:10s} {ch:3d}/{len(grp):3d}  {pct}")

    # --- M1~M3 --------------------------------------------------------------
    print("\nM1 — C0 의 R3(지어낸 수치) 자리")
    for i in R3_C0:
        print(f"  {i:52s} {cell(rows[i])}" if i in rows else f"  {i} (못 찾음)")
    for label, ids in (("M2 — 잘함 회복", RECOVERED),
                       ("M3 — 방향 고쳐짐", FIXED),
                       ("M3 — 방향 악화", WORSE)):
        print(f"\n{label}")
        for i in ids:
            print(f"  {i:52s} {cell(rows[i])}")

    # --- 칸별 요약 ----------------------------------------------------------
    print("\n칸별 자리 수 (전체 80)")
    for two in (True, False):
        for ch in (True, False):
            n = sum(1 for r in rows.values()
                    if r["양방향"] is two and r["차례바뀜"] is ch)
            print(f"  {'양방향' if two else '한방향'} · "
                  f"{'차례바뀜' if ch else '차례그대로'} : {n}")


if __name__ == "__main__":
    main()
