#!/usr/bin/env python3
"""문구 검수 서식을 만든다 — 지도자에게 내밀 종이 (미결 2번, 문구 축).

    uv run python eval/pending2_wording/build_review_packet.py          # 미리보기
    uv run python eval/pending2_wording/build_review_packet.py --write  # 파일로

**무엇을 푸는가.** 선수가 화면에서 그대로 읽는 문장이 둘 있다 — 칭호(`titles`)와
추천 카드의 불릿(`card_lines`). 둘 다 **루브릭에 데이터로** 살고, 그렇게 둔
이유가 **사람이 검수할 수 있게** 하려는 것이었다. 🔴 그런데 검수하려면 내밀
종이가 있어야 한다. 이 스크립트가 그것을 만든다.

🔴 **옆 폴더(`pending2_bands`)와 묻는 것이 다르다.** 거기는 **숫자**(구간)를
묻고 여기는 **말**을 묻는다. 한 장에 합치지 않은 이유는 섞으면 지도자가 한 번에
둘을 판단하게 되고, 돌아온 답이 어느 쪽에 대한 것인지 모르게 되기 때문이다.
같은 자리에서 두 장을 내미는 것은 된다 — 문구 쪽이 훨씬 빨리 끝난다.

🔴 **문장을 여기서 고치지 않는다.** 이 스크립트는 루브릭을 읽기만 한다. 받은
답은 루브릭에 반영하고 서식을 다시 뽑는다 — 사본을 손으로 고치면 두 판이 생긴다.

🔴 **처방을 미리 적지 않는다** (옆 폴더와 같은 규칙). 어색해 보이는 문장을 알고
있어도 서식에 표시하지 않는다. 유도하면 검수가 아니라 확인이 된다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import Rubric, discover_rubrics  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "packet"

# 등급을 번호 없이 부르는 낱말. `judge.LEVEL_WORDS` 와 같은 말을 쓴다 — 지도자가
# 보는 종이와 모델이 보는 프롬프트가 다른 낱말을 쓰면 나중에 대조가 안 된다.
LEVEL_WORDS = {2: "잘함", 1: "보통", 0: "아쉬움"}

INTRO = """\
## 무엇을 봐 주시면 되나요

선수가 **화면에서 그대로 읽는 문장** 둘입니다.

| | 어디에 보이나 |
|---|---|
| **칭호** | 분석 결과에서 항목 이름 옆. 추천 목록에서는 **「잘함」 등급만** 이름 아래 수식어로 씁니다 |
| **카드 문장** | 추천 목록에서 선수 이름 아래 한 줄 |

🔴 **추천 목록에는 그 선수의 「가장 잘한 등급」만 보입니다.** 잘한 항목이 하나라도
있으면 **「잘함」 문장만** 보이고, 아쉬운 항목은 **거기 안 나옵니다**(본인이 보는
분석 결과에는 그대로 있습니다). 그래서 「보통」·「아쉬움」 문장은 **잘한 항목이
하나도 없는 선수에게만** 보입니다 — 그 자리에서도 읽을 만한 말인지 봐 주시면
됩니다.

**세 가지만 봐 주시면 됩니다.**

1. **그 구간의 동작을 맞게 부르고 있습니까.** 「보통」 자리의 문장이 실제로는
   「아쉬움」에 가까운 말을 하고 있지는 않은지.
2. **선수가 읽어도 되는 말입니까.** 아쉬운 등급이라도 **무엇을 고치면 되는지**가
   보이면 좋고, 사람을 깎는 말이면 안 됩니다.
3. **「잘함」 문장이 칭찬으로 읽힙니까.** 한 번 틀린 자리입니다 — 잘한 항목에
   지적처럼 들리는 칭호가 붙어 있었습니다.

## 숫자는 이 종이에서 안 여쭙니다

표의 「기준」 칸은 그 문장이 **어느 동작을 가리키는지** 알려드리려고 같이 놓은
것입니다. 🔴 **그 숫자가 맞는지는 다른 종이에서 따로 여쭙습니다.** 지금은 전부
검수 전 임시값입니다 — 숫자가 이상해 보이시면 문장 대신 그 점만 한 줄 적어
주십시오.

## 답은 어떻게 적나요

**고치실 문장만** 맨 오른쪽 칸에 적어 주십시오. 비워 두시면 「그대로 좋다」로
읽습니다. 문장에 세 가지는 넣지 말아 주십시오.

- **숫자를 넣지 마십시오.** 같은 등급이면 모든 선수가 같은 문장을 받습니다 —
  「약 16cm」를 적으면 그 구간의 모든 영상이 **재지도 않은 수치**를 달고 나갑니다.
- **경기 이야기를 넣지 마십시오**(「10경기 연속」·「활동량이 많고」). 이 분석이
  본 것은 **영상 한 편의 자세**뿐입니다.
- **그 항목 하나만** 말해 주십시오. 총평과 등급 표기는 화면이 따로 붙입니다.

「이 문장은 아예 빼는 게 낫다」도 답으로 받습니다.
"""


def render(rubric: Rubric) -> str:
    state = "열려 있는 동작" if rubric.is_active else "아직 안 연 동작"
    out = [f"# 문구 검수 서식 — {rubric.label}", ""]
    out.append(f"<small>{state} · 항목 {len(rubric.criteria)}개 · "
               f"이 종이는 `eval/pending2_wording/build_review_packet.py` 가 "
               f"루브릭에서 뽑았습니다. 표를 직접 고치지 마십시오.</small>")
    out.append("")
    out.append(INTRO)
    for n, c in enumerate(rubric.criteria, 1):
        out.append(f"\n---\n\n## {n}. {c.name}\n")
        if c.rationale:
            out.append(f"> {' '.join(c.rationale.split())}\n")
        out.append("| 등급 | 기준 (참고용 — 이 종이의 질문 아님) | 칭호 | "
                   "카드 문장 | 🖊 고치실 문장 |")
        out.append("|---|---|---|---|---|")
        for g in (2, 1, 0):
            out.append(
                f"| **{LEVEL_WORDS[g]}** | {c.grades.get(g) or '—'} "
                f"| {c.titles.get(g) or '🔴 **비어 있습니다**'} "
                f"| {c.card_lines.get(g) or '🔴 **비어 있습니다**'} |  |"
            )
    out.append("\n---\n")
    out.append("## 마지막으로")
    out.append("")
    out.append("이 동작에서 **선수에게 꼭 해 주고 싶은 말**인데 위 항목 어디에도"
               " 없는 것이 있으면 적어 주십시오. 항목 자체가 빠졌다는 뜻일 수"
               " 있습니다.")
    out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help=f"{OUT_DIR} 에 파일로 쓴다")
    args = ap.parse_args()

    rubrics = discover_rubrics(ROOT / "rubrics")
    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key in sorted(rubrics):
        rubric = rubrics[key]
        text = render(rubric)
        if args.write:
            path = OUT_DIR / f"{rubric.sport}_{rubric.motion}.md"
            path.write_text(text, encoding="utf-8")
            print(f"쓰기: {path.relative_to(ROOT)}")
        else:
            print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
