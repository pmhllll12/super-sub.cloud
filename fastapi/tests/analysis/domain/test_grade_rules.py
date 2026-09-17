"""analysis/domain/rules/grade_rules.py — 표시 등급(S~F). **HTTP도 DB도 없다.**

수치는 `jekyll/pages/pending.markdown`의 `paik` 26번(정상호 회신, 2026-09-14)
표와 그대로 맞춘다 — 값이 달라지면 그 표도 같이 확인한다.
"""

from __future__ import annotations

import pytest

from app.analysis.domain.rules.grade_rules import (
    display_grade,
    is_trust_dominant,
    wilson_lower_bound,
)


class TestWilsonLowerBound:
    def test_리뷰가_없으면_0이다(self):
        assert wilson_lower_bound(0, 0) == 0.0

    @pytest.mark.parametrize(
        "positive, total, expected",
        [
            (1, 1, 0.207),
            (3, 3, 0.439),
            (4, 4, 0.510),
            (6, 7, 0.487),
            (7, 8, 0.529),
            (9, 11, 0.523),
        ],
    )
    def test_26번_표의_하한값과_일치한다(self, positive, total, expected):
        assert wilson_lower_bound(positive, total) == pytest.approx(
            expected, abs=1e-3
        )


class TestIsTrustDominant:
    def test_리뷰가_하나도_없으면_우세가_아니다(self):
        assert is_trust_dominant(0, 0) is False

    def test_한_건으로는_갈리지_않는다(self):
        assert is_trust_dominant(1, 1) is False

    def test_전원_긍정_4건이면_우세다(self):
        assert is_trust_dominant(4, 4) is True

    def test_전원_긍정_3건은_아직_아니다(self):
        assert is_trust_dominant(3, 3) is False

    def test_부정_1건_섞이면_8건은_돼야_우세다(self):
        assert is_trust_dominant(6, 7) is False
        assert is_trust_dominant(7, 8) is True


class TestDisplayGrade:
    def test_리뷰_없는_A는_S가_아니다(self):
        assert display_grade("A", trust_dominant=False) == "A"

    def test_신뢰_우세인_A는_S다(self):
        assert display_grade("A", trust_dominant=True) == "S"

    def test_신뢰_우세_아닌_D는_F로_내려간다(self):
        assert display_grade("D", trust_dominant=False) == "F"

    def test_신뢰_우세인_D는_그대로_D다(self):
        assert display_grade("D", trust_dominant=True) == "D"

    def test_B와_C는_신뢰축과_무관하게_그대로다(self):
        assert display_grade("B", trust_dominant=True) == "B"
        assert display_grade("C", trust_dominant=False) == "C"

    def test_분석_전이면_None_그대로다(self):
        assert display_grade(None, trust_dominant=True) is None
