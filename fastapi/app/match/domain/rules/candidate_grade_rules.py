"""표시 등급(`S`~`F`) 재계산 + 추천 후보의 실력 축 거리. `paik` 27번.

🔴 **`app/analysis/domain/rules/grade_rules.py`와 같은 식이다 — 가져오지
않는다.** 컨텍스트끼리 임포트하지 않는 경계(`fastapi/CLAUDE.md`) 때문에
순수 함수라도 복제한다. `review_rules.py`의 `OWNER_ROLE`과 같은 판단이다.
**둘이 갈리면 여기 값이 아니라 `grade_rules.py`가 정본이다** — 26번 회신
(`pending.markdown`)이 그 식의 근거를 담고 있다.
"""

from __future__ import annotations

_Z = 1.959963985


def wilson_lower_bound(positive: int, total: int) -> float:
    if total <= 0:
        return 0.0
    z2 = _Z * _Z
    phat = positive / total
    denom = 1 + z2 / total
    center = phat + z2 / (2 * total)
    margin = _Z * ((phat * (1 - phat) + z2 / (4 * total)) / total) ** 0.5
    return (center - margin) / denom


def is_trust_dominant(positive: int, total: int) -> bool:
    return wilson_lower_bound(positive, total) > 0.5


def display_grade(overall_grade: str | None, trust_dominant: bool) -> str | None:
    if overall_grade == "A" and trust_dominant:
        return "S"
    if overall_grade == "D" and not trust_dominant:
        return "F"
    return overall_grade


# 실력 축 4칸(`paik` 27번, 정상호 회신) — `S`는 `A`, `F`는 `D`와 같은 자리다.
# `S`~`F` 를 그대로 등간으로 세면 「등급이 아니라 리뷰 유무」가 실력차로
# 둔갑한다(회신의 `averageGrade([S, D])` 사례) — 그래서 표시 등급이 아니라
# 이 4칸에서 거리를 잰다.
_SKILL_VALUE = {"F": 0, "D": 0, "C": 1, "B": 2, "A": 3, "S": 3}


def skill_value(grade: str | None) -> int | None:
    """실력 축 값(0~3). 등급을 모르면 `None` — 0 으로 치지 않는다(`ho` 21번과
    같은 판단, 모르는 것과 낮은 것은 다르다)."""
    if grade is None:
        return None
    return _SKILL_VALUE.get(grade)
