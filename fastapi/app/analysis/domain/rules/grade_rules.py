"""표시 등급(`S`~`F`) 규칙. 미결 `paik` 26번 — 정상호가 정한 값(2026-09-14)을
여기서 구현한다. **HTTP도 DB도 없다** — `review_rules.py`(패킷 B)와 같은 자리다.

분석 등급(`A`~`D`) 위에 **신뢰 우세**(재매칭 의사의 95% Wilson 신뢰구간 하한이
과반을 넘는가)를 얹는다. `S`는 "`A`인데 올려 줄 근거가 있다", `F`는 "`D`인데
구해 줄 근거가 없다" — 증거 없음(리뷰 0건)은 어느 쪽으로도 안 민다. 근거·경계값
산출 과정 전체는 `jekyll/pages/pending.markdown`의 `paik` 26번을 본다. **숫자를
손으로 바꾸지 말고 거기 식에서 다시 뽑는다** — 바꾸면 아래 4·8·11건 표가 같이
움직인다.
"""

from __future__ import annotations

# 95% 양측 표준정규 분위수. `paik` 26번의 신뢰구간 하한 계산에 쓰인 값과 같다.
_Z = 1.959963985


def wilson_lower_bound(positive: int, total: int) -> float:
    """재매칭 긍정 비율의 95% 신뢰구간 **하한**.

    비율 대신 하한을 쓰는 이유: 표본이 작을수록 저절로 불리해져서 "한 건으로
    `S`가 갈리면 안 된다"가 규칙을 따로 안 써도 만족된다(1건 전원 긍정의
    하한은 0.207).
    """
    if total <= 0:
        return 0.0
    z2 = _Z * _Z
    phat = positive / total
    denom = 1 + z2 / total
    center = phat + z2 / (2 * total)
    margin = _Z * ((phat * (1 - phat) + z2 / (4 * total)) / total) ** 0.5
    return (center - margin) / denom


def is_trust_dominant(positive: int, total: int) -> bool:
    """신뢰 우세 — 하한이 **과반(0.5)** 을 넘는가.

    0.5는 고른 값이 아니라 비율 축에서 임의적이지 않은 유일한 점이라 썼다
    (`paik` 26번 ⑵). 그래서 최소 건수도 따로 정하지 않았다 — 전원 긍정이면
    4건, 부정이 하나라도 섞이면 8건이 이 식에서 그대로 나온다.
    """
    return wilson_lower_bound(positive, total) > 0.5


def display_grade(overall_grade: str | None, trust_dominant: bool) -> str | None:
    """분석 등급 + 신뢰 우세 → 표시 등급.

    `S`와 `F`는 같은 문턱의 양쪽이다. `D`가 `F`로 내려가는 것은 강등이 아니라
    "구해 줄 근거가 없어 `D`에 머무는 것"이라고 읽는다 — 그래서 리뷰가 하나도
    없어도(`trust_dominant=False`) `A`는 그대로 `A`고, `D`만 `F`로 보인다.
    분석 자체가 없으면(`overall_grade is None`) 그대로 `None`을 돌려준다.
    """
    if overall_grade == "A" and trust_dominant:
        return "S"
    if overall_grade == "D" and not trust_dominant:
        return "F"
    return overall_grade
