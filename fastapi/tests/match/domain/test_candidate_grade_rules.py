"""match/domain/rules/candidate_grade_rules.py — `paik` 27번.

`analysis/domain/rules/grade_rules.py`와 값이 같아야 한다(복제, 임포트 금지
— `fastapi/CLAUDE.md`). 표는 `tests/analysis/domain/test_grade_rules.py`와
같은 값이다.
"""

from __future__ import annotations

import pytest

from app.match.domain.rules.candidate_grade_rules import (
    display_grade,
    is_trust_dominant,
    skill_value,
    wilson_lower_bound,
)


class TestWilsonLowerBound:
    @pytest.mark.parametrize(
        "positive, total, expected",
        [(1, 1, 0.207), (4, 4, 0.510), (7, 8, 0.529)],
    )
    def test_analysis_쪽_값과_같다(self, positive, total, expected):
        assert wilson_lower_bound(positive, total) == pytest.approx(
            expected, abs=1e-3
        )


class TestIsTrustDominant:
    def test_리뷰가_없으면_우세가_아니다(self):
        assert is_trust_dominant(0, 0) is False

    def test_전원_긍정_4건이면_우세다(self):
        assert is_trust_dominant(4, 4) is True


class TestDisplayGrade:
    def test_신뢰_우세인_A는_S다(self):
        assert display_grade("A", trust_dominant=True) == "S"

    def test_신뢰_우세_아닌_D는_F다(self):
        assert display_grade("D", trust_dominant=False) == "F"

    def test_분석_전이면_None이다(self):
        assert display_grade(None, trust_dominant=True) is None


class TestSkillValue:
    def test_S와_A는_같은_자리다(self):
        assert skill_value("S") == skill_value("A") == 3

    def test_F와_D는_같은_자리다(self):
        assert skill_value("F") == skill_value("D") == 0

    def test_등급을_모르면_None이다(self):
        """0으로 치지 않는다 — 모르는 것과 낮은 것은 다르다(`ho` 21번)."""
        assert skill_value(None) is None
