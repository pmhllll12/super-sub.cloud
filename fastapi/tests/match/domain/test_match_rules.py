"""match/domain/rules/match_rules.py — 아무것도 안 띄우고 규칙만 본다."""

from datetime import datetime, timedelta, timezone

from app.match.domain.rules.match_rules import can_register, is_registrable

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


class TestCanRegister:
    def test_주장만_등록한다(self):
        assert can_register("owner") is True
        assert can_register("member") is False

    def test_소속이_아니면_못_한다(self):
        """소속이 아니면 역할이 None 으로 온다."""
        assert can_register(None) is False


class TestIsRegistrable:
    def test_앞으로의_경기는_등록된다(self):
        assert is_registrable(NOW + timedelta(minutes=1), NOW) is True

    def test_지난_경기는_안_된다(self):
        assert is_registrable(NOW - timedelta(minutes=1), NOW) is False

    def test_같은_시각도_안_된다(self):
        """지금 시작하는 경기를 모집할 수는 없다."""
        assert is_registrable(NOW, NOW) is False
