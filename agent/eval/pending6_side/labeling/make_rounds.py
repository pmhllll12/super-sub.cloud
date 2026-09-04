#!/usr/bin/env python3
"""미결 6번 2차 판독 — **한 회차에 한 칸만 묻는** 서식을 만든다.

    uv run python eval/pending6_side/labeling/make_rounds.py

이미지를 새로 만들지 않는다. 1차 판독이 쓴 `review_packet/images/` 39장을
그대로 쓴다 — 그림에는 결함이 없었다. 고치는 것은 **묻는 방식**이다.

## 왜 회차를 나누는가

1차 서식은 한 줄에 네 칸(`top_hand`·`swing_arm`·`swing_leg`·`subject_ok`)을
나란히 두었고, 안내문이 「`top_hand`부터 채우면 빠릅니다」라고 순서까지
권했다. 그 결과 받은 12건에서:

    swing_arm 이 both 가 아닌 8건이 **전부** top_hand 의 반대쪽이었다
    같은 8건에서 swing_leg 도 swing_arm 과 **전부** 같았다

🔴 **12건으로는 두 해석을 못 가른다** — 판독자가 `top_hand`를 정하고 나머지를
규칙으로 도출한 것인지, 우타자의 위쪽 손이 오른손이고 디딤발이 왼발인
**실제 신체 상관**인지. 어느 쪽이든 **세 칸이 독립 관측이라는 것을 지금
서식은 보장하지 못한다.** 상관이 진짜여도 마찬가지다 — 진짜인지 아닌지를
이 서식으로는 물을 수 없다는 것이 결함이다.

그래서 회차를 나눈다. 한 화면에 한 질문만 있으면 **옆 칸을 보고 채울 수
없다.**

## 회차 순서 — 도출당하기 쉬운 칸을 뒤에 둔다

    1  subject_ok   스켈레톤이 타자에게 붙었는가
    2  swing_leg    크게 움직인 다리
    3  swing_arm    스윙한 팔
    4  top_hand     배트 위쪽 손

`top_hand`가 **마지막**이다. 1차에서 그것이 첫 칸이었고 나머지가 그 여집합
으로 나왔다. 가장 쉽고 확실한 칸이라 순서를 뒤로 미뤄도 정확도가 떨어지지
않는다 — 반대로 앞에 두면 나머지 셋의 기준점이 된다.

`subject_ok`가 **처음**이다. 스켈레톤이 타자가 아니면 나머지 세 칸은 다른
사람의 팔다리를 가리킨다. 먼저 물어야 뒤 회차의 답을 해석할 수 있다.

## 순서를 회차마다 섞는다

같은 순서로 네 번 주면 3회차쯤엔 "이 줄은 아까 그 클립"이라고 세로로 맞출 수
있다. 회차마다 다른 순서로 섞어 그걸 막는다. **시드를 고정**하므로 다시
돌려도 같은 파일이 나온다 — 재현 가능해야 나중에 무엇을 보고 채웠는지 되짚는다.

⚠️ **이것이 기억까지 막지는 못한다.** 같은 39장을 네 번 보는 사람은 그림을
알아본다. 회차 분리가 막는 것은 **옆 칸을 보고 채우는 것**이고, 기억으로
맞추는 것까지 막으려면 **회차마다 판독자가 달라야 한다.** 그것은 서식이
아니라 인력 문제라 여기서 해결하지 않는다 — `INSTRUCTIONS.md`에 적어 둔다.

## 어휘를 바꾸지 않았다

네 칸의 허용값은 1차와 **완전히 같다.** 바꾸면 12건과 나란히 놓을 수 없고,
사전 등록(`AFTER_LABELS.md`)과 그 구현(`labeled_stats.py`)이 못 읽는다.
`merge_rounds.py`가 회차들을 1차와 같은 모양의 서식 한 장으로 되붙이므로
**기존 분석 코드는 고치지 않는다.**
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "review_packet" / "images"
OUT = HERE / "review_packet2"

# 🔴 **고정 시드다.** 바꾸면 회차 순서가 달라져 이미 배포한 서식과 어긋난다.
# 값 자체에 의미는 없다(서식을 만든 날짜).
SEED = 20260904

# (파일명, 답 칸, 그 회차에서 함께 받는 칸)
# 순서가 곧 판독 순서다 — 위 docstring 「회차 순서」 참고.
ROUNDS = [
    ("round1_subject.csv", "subject_ok", ["seen_before"]),
    ("round2_leg.csv", "swing_leg", []),
    ("round3_arm.csv", "swing_arm", []),
    ("round4_top_hand.csv", "top_hand", []),
]


def clip_ids() -> list[str]:
    """판독 대상 39클립.

    **`reference_AFTER_LABELING.csv`를 읽지 않는다.** 그 파일에는 알고리즘이
    고른 답이 들어 있어서, 서식을 만드는 경로가 그것을 스치기만 해도 나중에
    "정말 안 보고 만들었나"를 증명할 수 없다. 이미지 폴더가 곧 대상 명단이다.
    """
    ids = sorted(p.stem for p in IMAGES.glob("*.jpg"))
    if not ids:
        raise SystemExit(f"이미지가 없다: {IMAGES}")
    return ids


def main() -> None:
    ids = clip_ids()
    OUT.mkdir(exist_ok=True)

    for i, (name, answer, extra) in enumerate(ROUNDS, start=1):
        order = ids[:]
        # 회차마다 다른 순서. 시드가 고정이라 결과는 결정적이다.
        random.Random(SEED + i).shuffle(order)

        path = OUT / name
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["no", "clip_id", "image", answer, *extra, "note"])
            for n, cid in enumerate(order, start=1):
                w.writerow([n, cid, f"../review_packet/images/{cid}.jpg",
                            "", *["" for _ in extra], ""])
        print(f"{path.name}: {len(order)}행 · 답 칸 {answer!r}")

    print(f"\n대상 {len(ids)}클립 · 시드 {SEED} · 이미지는 {IMAGES} 를 그대로 쓴다")
    print("판독 절차: review_packet2/INSTRUCTIONS.md")


if __name__ == "__main__":
    main()
