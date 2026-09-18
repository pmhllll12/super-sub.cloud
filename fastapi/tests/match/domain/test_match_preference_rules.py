"""`match/domain/rules/match_preference_rules.py` — 시간 겹침·지역 계층.

🔴 **이 규칙이 「탐색이 되느냐」를 혼자 정한다.** 빈 자리 후보(`paik` 27번)의
마지막 하드 필터가 `overlap_minutes(...) > 0` 이고, 맞는 상대(`paik` 20번)의
점수도 여기서 나온다. 그런데 2026-09-18 까지 **직접 거는 시험이 없었다** —
운영에서 심사위원 팀이 「월 15:00~15:30」이라 후보가 0명이던 것을 보고서야
이 자리가 비어 있는 것을 알았다.

사용자 물음(2026-09-18): 「시간이 정확히 일치해야 찾을 수 있는 거야?」
→ **아니다. 겹치면 된다.** 다만 **요일은 같아야 한다.** 그 둘을 여기서 못 박는다.
"""

from __future__ import annotations

from datetime import time

from app.match.domain.rules.match_preference_rules import overlap_minutes, region_tier


def t(h: int, m: int = 0) -> time:
    return time(h, m)


class TestOverlapMinutes:
    """🔴 **정확히 일치할 필요가 없다** — 겹친 만큼을 분으로 돌려준다."""

    def test_똑같은_시간대면_그_길이가_나온다(self):
        assert overlap_minutes(5, t(10), t(12), 5, t(10), t(12)) == 120

    def test_일부만_겹쳐도_통과한다(self):
        """🔴 이것이 사용자가 걱정한 자리다 — 부분 겹침으로 충분하다."""
        assert overlap_minutes(5, t(10), t(12), 5, t(11), t(15)) == 60

    def test_한쪽이_다른_쪽을_통째로_감싸면_안쪽_길이다(self):
        assert overlap_minutes(5, t(8), t(18), 5, t(10), t(12)) == 120

    def test_1분만_겹쳐도_0_이_아니다(self):
        """하드 필터가 `> 0` 이라, 1분이 곧 「찾을 수 있다」의 경계다."""
        assert overlap_minutes(5, t(10), t(12), 5, t(11, 59), t(13)) == 1

    def test_맞닿기만_하면_0_이다(self):
        """끝과 시작이 같은 것은 겹친 것이 아니다 — 같이 뛸 시간이 없다."""
        assert overlap_minutes(5, t(10), t(12), 5, t(12), t(14)) == 0

    def test_안_겹치면_0_이다(self):
        assert overlap_minutes(5, t(10), t(12), 5, t(13), t(15)) == 0

    def test_요일이_다르면_아무리_겹쳐도_0_이다(self):
        """🔴 **여기가 유일하게 빡빡한 곳이다.**

        시각은 범위로 보지만 요일은 **정확히 같아야** 한다 — 토요일 10~12 와
        일요일 10~12 는 전혀 안 맞는 것으로 친다. 운영에서 심사위원 팀이
        「월 15:00~15:30」이었고 후보들은 화·목·토·일만 열어 두어, 이 한 줄
        때문에 추천이 0명이었다(2026-09-18).
        """
        assert overlap_minutes(0, t(10), t(12), 5, t(10), t(12)) == 0
        assert overlap_minutes(5, t(0), t(23, 59), 6, t(0), t(23, 59)) == 0


class TestRegionTier:
    """🔴 지역도 **완전일치가 아니다** — 3단계다(`paik` 20번 정상호 회신)."""

    def test_같은_구면_district(self):
        assert region_tier("서울", "강남구", "서울", "강남구") == "district"

    def test_같은_시_다른_구면_city(self):
        assert region_tier("서울", "강남구", "서울", "마포구") == "city"

    def test_시가_다르면_none(self):
        assert region_tier("서울", "강남구", "부산", "해운대구") == "none"
