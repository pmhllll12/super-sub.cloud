"""판독 계기 — 문장을 **절로 쪼개** 자리마다 맞는 방향과 나란히 낸다 (미결 23번 D).

    uv run python eval/pending23_evidence/split_clauses.py --out reading_sheet.json
    uv run python eval/pending23_evidence/split_clauses.py --shuffled --out sheet2.json

사전 등록: `PREREGISTRATION_reading.md`. 결과를 보고 이 스크립트를 고치지 않는다.

## 🔴 왜 만들었나 — 규칙이 아니라 **적용**이 빠졌다

판정 규칙은 「문장이 **반대 조각의 방향을 주장하는 절**을 포함하면 오독」이다.
「포함하면」은 **모든 절을 봐야** 성립하는데, 읽는 사람이 그것을 보장할 방법이
없었다. 그래서 B 회차가 겨냥한 어구가 사라진 것을 확인하고 **첫 마침표에서
멈췄고**, 같은 문장이 B 3/30 · C 5/30 으로 갈렸다.

    "…79.2도로 패스보다 슈팅처럼 과도하게 뻗은 마무리다."   ← 맞다
    "추가 굴곡이 부족해 공이 공중에 뜨는 느낌이 강하다."      ← 반대다. 놓쳤다

이 스크립트가 고치는 것은 **판단이 아니라 열거**다. 절을 다 늘어놓으면
넘어갈 절이 없다.

## 쪼개는 규칙 — 🔴 **과하게 쪼개는 쪽으로 틀린다**

덜 쪼개면 절이 숨고 그것이 지금 고치는 결함이다. 과하게 쪼개면 판정할 것이
늘 뿐 숨는 것은 없다. 그래서 경계를 넉넉히 잡는다.

  ⑴ 문장 끝: `.` `!` `?` `…` 와 화살표(`→`)
  ⑵ 연결 어미: `~며` `~고` `~나` `~지만` `~는데` `~아서/어서` `~여` `~으나`
     `~면서` `~되` 뒤에 **공백**이 오는 자리
  ⑶ 쉼표 뒤

경계가 **문자로 정해져 있어 결정론적**이다. 형태소 분석을 쓰지 않는다 —
새 의존을 부르고, 버전이 바뀌면 같은 문장이 다르게 쪼개진다.

## 판정은 여기서 안 한다

이 스크립트는 **읽을 것을 늘어놓기만** 한다. 절마다 ok/wrong 은 사람이
적는다(`verdict` 를 비워 둔다). 🔴 문자열로 방향을 가르려 하지 않는다 —
23번 본문이 「그 검사가 또 틀리고, 틀린 검사는 검사했다는 인상만 남긴다」고
적어 둔 그것이다.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import discover_rubrics  # noqa: E402

#: 절 경계. 🔴 **과하게 쪼개는 쪽으로** 틀리게 골랐다 (머리말).
#: 어미 뒤에 공백을 요구해 「부족해」 같은 명사 끝을 안 자른다.
_ENDINGS = ("며", "고", "나", "지만", "는데", "아서", "어서", "여", "으나",
            "면서", "되")
#
# 🔴 어미마다 **따로** 룩비하인드를 둔다 — 하나로 묶으면 길이가 달라
# `look-behind requires fixed-width pattern` 이 난다. 각각은 고정 길이다.
_BOUNDARY = re.compile(
    r"(?<=[.!?…])\s+"                                  # ⑴ 문장 끝
    r"|\s*→\s*"                                        # ⑴ 화살표
    r"|(?:" + "|".join(f"(?<={e})" for e in _ENDINGS) + r")\s+"   # ⑵ 연결 어미
    r"|(?<=,)\s+"                                      # ⑶ 쉼표 뒤
)


def clauses(text: str) -> list[str]:
    """문장을 절로. 🔴 **빈 절은 버리되 하나도 없으면 원문을 그대로 돌려준다** —
    쪼개기가 실패해도 읽을 것이 사라지면 안 된다."""
    parts = [p.strip() for p in _BOUNDARY.split(text) if p and p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="evidence_other_levels.json",
                    help="읽을 문장 파일 (기본값 = C0 = B 회차 산출물)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--shuffled", action="store_true",
                    help="2차 판독용 — 순서를 섞고 자리 이름을 가린다")
    ap.add_argument("--seed", type=int, default=23,
                    help="섞는 씨앗. 🔴 고정값이라 2차도 재현된다")
    args = ap.parse_args()

    rubrics = discover_rubrics(str(ROOT / "rubrics"))
    data = json.loads((HERE / args.src).read_text(encoding="utf-8"))

    rows = []
    for key, payload in data["clips"].items():
        for item in payload["items"]:
            criterion = rubrics[key].get(item["criterion_id"])
            grade = item["grade"]
            # D 판독 대상 = **한 등급에 반대 방향 조각이 둘인 자리**.
            if len(criterion.bands[grade]) < 2:
                continue
            value = item["given_metrics"][criterion.band_metric]
            seg = next(
                i for i, (lo, hi) in enumerate(criterion.bands[grade])
                if (lo is None or value >= lo) and (hi is None or value <= hi)
            )
            written = criterion.grades_plain.get(grade, ())
            rows.append({
                "id": f"{key.split('/')[-1]}/{criterion.id}/{value}",
                "맞는_방향": criterion.plain_for(grade, value),
                # 🔴 **반대 조각의 말을 함께 적는다.** 판정 규칙이 「반대
                #    조각의 방향을 주장하는가」라, 무엇이 반대인지 눈앞에
                #    없으면 읽는 사람이 그때그때 떠올려야 한다.
                "반대_방향": [t for i, t in enumerate(written) if i != seg],
                "절": [{"절": c, "verdict": ""} for c in clauses(item["evidence"])],
                "_원문": item["evidence"],
            })

    if args.shuffled:
        random.Random(args.seed).shuffle(rows)
        for n, row in enumerate(rows, 1):
            row["_가린_id"] = row.pop("id")   # 2차는 자리 이름을 안 본다
            row["id"] = f"Q{n:02d}"

    dest = HERE / args.out
    dest.write_text(json.dumps(
        {"_설명": "절마다 verdict 를 ok/wrong 으로 채운다. 빈 칸이 남으면 "
                  "그 자리는 안 읽은 것이다 (미결 23번 D).",
         "_출처": args.src, "_섞음": args.shuffled,
         "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    n_clause = sum(len(r["절"]) for r in rows)
    print(f"{len(rows)}자리 · 절 {n_clause}개 → {dest.relative_to(ROOT)}")
    print(f"자리당 절 중앙 {sorted(len(r['절']) for r in rows)[len(rows)//2]}개 "
          f"· 최대 {max(len(r['절']) for r in rows)}개")


if __name__ == "__main__":
    main()
