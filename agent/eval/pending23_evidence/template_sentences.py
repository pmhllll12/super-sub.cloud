"""문장을 **코드가 조립한다** — 모델 없이 (미결 23번 J, 자료 회차).

    uv run python eval/pending23_evidence/template_sentences.py

🔴 **판정 회차가 아니다.** 사전 등록한 기준(R1·R2·R2′·R3·방향 오독)은 이쪽에서
**자명하게 통과한다** — 문장에 쓰는 숫자가 준 측정값 하나뿐이고 방향은
루브릭이 정한 것을 그대로 옮기기 때문이다. **통과했다고 「이겼다」고 적으면
안 된다.** 이 회차가 내놓는 것은 **판단 자료**이고, 물음은 하나다:

    이 문장이 선수에게 보여 줄 만한가?

그건 숫자가 아니라 **제품 판단**이라 사람이 정한다.

## 왜 만들었나

23번에서 아홉 회차(가-2 ~ I)를 돌리며 프롬프트로 방향 오독을 줄이려 했는데,
**F 이후 세 번 연속 「한쪽을 조이면 다른 쪽이 무너진다」**가 났다. 틀린 문장의
총량이 5 언저리에서 안 움직인다.

그런데 **방향은 이미 코드가 안다** — `grades_plain[등급][조각]` 이
「골반을 지나치게 많이 돌린다」라고 정확히 말해 주고, `card_lines` 는 아예
**선수에게 보여 줄 문장**으로 쓰여 있다(지도자 검수 대상으로 루브릭에 둔 것).

「등급 판정을 모델에서 코드로 옮긴」 것과 **같은 수를 문장에도 두는 것**이
이 자료가 보여 주려는 길이다.

## 두 가지로 조립한다

    T1  지표 + 값 + `grades_plain`   — 자세 서술, 평어
    T2  지표 + 값 + `card_lines`     — 이미 선수용으로 쓴 문장, 존댓말

🔴 **`src/` 를 안 고친다.** production 을 import 만 하고, 조립 규칙은 여기
안에만 있다. 채택되면 그때 제품으로 옮기는 것이 별도 일이다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.judge import label_for, valued  # noqa: E402
from supersub_agent.scoring import discover_rubrics  # noqa: E402

F_FILE = "evidence_anchor_order.json"   # 지금 제품(F 회차)의 출력


def t1(criterion, metrics: dict, grade: int) -> str:
    """지표 + 값 + 자세 서술(`grades_plain`). 🔴 값은 **준 것 하나만** 쓴다."""
    value = metrics.get(criterion.band_metric)
    plain = criterion.plain_for(grade, value)
    head = (f"{label_for(criterion.band_metric, criterion.name)} "
            f"{valued(criterion.band_metric, value)}")
    # 🔴 `grades_plain` 이 비면 **문장을 지어내지 않고** 머리만 낸다 —
    #    `plain_for` 가 빈 문자열로 떨어지는 것과 같은 판단이다(scoring.py).
    return f"{head} — {plain}" if plain else head


def t2(criterion, metrics: dict, grade: int) -> str:
    """지표 + 값 + `card_lines`. 카드 불릿은 이미 **선수에게 보여 줄 문장**이다."""
    value = metrics.get(criterion.band_metric)
    line = criterion.card_line_for(grade, value)
    head = (f"{label_for(criterion.band_metric, criterion.name)} "
            f"{valued(criterion.band_metric, value)}")
    return f"{head} — {line}" if line else head


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="SIDE_BY_SIDE_template.md")
    args = ap.parse_args()

    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    data = json.loads((HERE / F_FILE).read_text(encoding="utf-8"))

    rows = []
    for key, payload in data["clips"].items():
        for item in payload["items"]:
            criterion = rubrics[key].get(item["criterion_id"])
            grade = item["grade"]
            metrics = item["given_metrics"]
            value = metrics[criterion.band_metric]
            rows.append({
                "자리": f"{key.split('/')[-1]}/{criterion.id}",
                "값": value,
                "등급": grade,
                "양방향": len(criterion.bands[grade]) > 1,
                "F(모델)": item["evidence"],
                "T1": t1(criterion, metrics, grade),
                "T2": t2(criterion, metrics, grade),
            })
    rows.sort(key=lambda r: (r["자리"], -r["등급"], r["값"]))

    # --- 🔴 「자명하게 통과한다」를 **주장하지 않고 검사기에 넘긴다** -------
    #     기존 `check_evidence.py`·`check_boundaries.py` 가 읽는 모양으로
    #     따로 내보내, 같은 R1·R2·R2′·R3 를 그대로 돌려 볼 수 있게 한다.
    for tag in ("t1", "t2"):
        out = {"tag": f"template_{tag}", "backend": "none", "model": "none",
               "clips": {}}
        for key, payload in data["clips"].items():
            items = []
            for item in payload["items"]:
                criterion = rubrics[key].get(item["criterion_id"])
                fn = t1 if tag == "t1" else t2
                items.append({**item,
                              "evidence": fn(criterion, item["given_metrics"],
                                             item["grade"])})
            out["clips"][key] = {"score": None, "grade": None, "items": items}
        (HERE / f"evidence_template_{tag}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    empty_t1 = sum(1 for r in rows if "—" not in r["T1"])
    empty_t2 = sum(1 for r in rows if "—" not in r["T2"])

    # 🔴 **문장 전체를 세면 안 된다.** 값이 문장에 들어가 자리마다 무조건
    #    달라지므로 「서로 다른 문장 수」는 80 에 붙어 버리고 **아무것도 안
    #    잰다**(처음에 그렇게 짰다가 고쳤다). 재려는 것은 **말의 가짓수**라
    #    값 뒤의 서술만 센다.
    def wording(text: str) -> str:
        return text.split("—", 1)[1].strip() if "—" in text else text

    uniq_f = len({wording(r["F(모델)"]) for r in rows})
    uniq_t1 = len({wording(r["T1"]) for r in rows})
    uniq_t2 = len({wording(r["T2"]) for r in rows})

    lines = [
        "# 곁에 놓고 보기 — 모델이 쓴 문장 vs 코드가 조립한 문장 (미결 23번 J)",
        "",
        "🔴 **판정 회차가 아니다.** 사전 등록한 기계 기준(R1·R2·R2′·R3·방향 오독)은",
        "템플릿 쪽에서 **자명하게 통과한다** — 쓰는 숫자가 준 측정값 하나뿐이고",
        "방향은 루브릭이 정한 것을 옮기기만 하기 때문이다. **「이겼다」가 아니다.**",
        "",
        "물음은 하나다 — **이 문장을 선수에게 보여 줄 만한가.** 제품 판단이다.",
        "",
        "| | |",
        "|---|---|",
        f"| 자리 | {len(rows)} |",
        f"| **서로 다른 「말」** | F(모델) **{uniq_f}** · T1 **{uniq_t1}** · T2 **{uniq_t2}** |",
        f"| 문장을 못 만든 자리 | T1 **{empty_t1}** · T2 **{empty_t2}** |",
        f"| 검사기 (R1·R2·R2′·R3) | T1·T2 **전부 0건** — 주장이 아니라 `evidence_template_*.json` 에 돌린 결과 |",
        "",
        "🔴 **말의 가짓수가 템플릿의 대가다.** 같은 등급·같은 조각이면 값만",
        "다르고 **말은 똑같다** — 80자리에서 모델은 76가지로 쓰는데 템플릿은",
        f"**{uniq_t1}가지**다. 리포트 여러 장을 이어 보면 **되풀이가 눈에 띈다.**",
        "",
        "🔴 **값을 포함한 문장 전체를 세면 이 대가가 안 보인다**(자리마다 값이",
        "달라 80에 붙는다). 처음에 그렇게 셌다가 고쳤다 — 계수가 재려는 것을",
        "재는지부터 봐야 한다는 것이 I 회차에서 배운 것과 같은 자리다.",
        "",
        "---",
        "",
    ]
    for r in rows:
        way = "양방향" if r["양방향"] else "한방향"
        lines += [
            f"### {r['자리']} · {r['값']} · {r['등급']}등급 ({way})",
            "",
            f"- **F(모델)**: {r['F(모델)']}",
            f"- **T1(자세 서술)**: {r['T1']}",
            f"- **T2(카드 문장)**: {r['T2']}",
            "",
        ]
    (HERE / args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(rows)}자리 → {(HERE / args.out).relative_to(ROOT)}")
    print(f"서로 다른 문장: F {uniq_f} · T1 {uniq_t1} · T2 {uniq_t2}")
    print(f"문장을 못 만든 자리: T1 {empty_t1} · T2 {empty_t2}")


if __name__ == "__main__":
    main()
