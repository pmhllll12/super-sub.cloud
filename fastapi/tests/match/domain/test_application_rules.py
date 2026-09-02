"""match/domain/rules/application_rules.py — 아무것도 안 띄우고 규칙만 본다."""

from datetime import datetime, timezone
from uuid import uuid4

from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.rules.application_rules import (
    SIDE_TEAM,
    SIDE_USER,
    acceptable_side,
    can_apply,
    can_offer,
    has_stake,
)

AT = datetime(2026, 9, 2, tzinfo=timezone.utc)
_APPLICANT = uuid4()
_OUTSIDER = uuid4()


def _app(team_at=None, user_at=None):
    return ApplicationEntity(
        id=uuid4(),
        match_id=uuid4(),
        user_id=_APPLICANT,
        nickname="지원자",
        team_accepted_at=team_at,
        user_accepted_at=user_at,
    )


class TestCanApply:
    def test_소속이_아닌_사람만_지원한다(self):
        """용병 매칭이라 자기 팀 경기에 지원하는 것은 뜻이 없다."""
        assert can_apply(None) is True
        assert can_apply("member") is False
        assert can_apply("owner") is False


class TestCanOffer:
    def test_제안은_주장만(self):
        assert can_offer("owner") is True
        assert can_offer("member") is False
        assert can_offer(None) is False


class TestAcceptableSide:
    def test_지원_건은_팀이_수락한다(self):
        app = _app(user_at=AT)
        assert acceptable_side(app, _OUTSIDER, actor_is_owner=True) == SIDE_TEAM

    def test_제안_건은_본인이_수락한다(self):
        app = _app(team_at=AT)
        assert acceptable_side(app, _APPLICANT, actor_is_owner=False) == SIDE_USER

    def test_자기_쪽은_다시_수락하지_않는다(self):
        app = _app(user_at=AT)
        assert acceptable_side(app, _APPLICANT, actor_is_owner=False) is None

    def test_확정된_건은_더_수락할_것이_없다(self):
        app = _app(team_at=AT, user_at=AT)
        assert acceptable_side(app, _APPLICANT, actor_is_owner=True) is None

    def test_무관한_사람은_못_한다(self):
        app = _app(user_at=AT)
        assert acceptable_side(app, _OUTSIDER, actor_is_owner=False) is None


class TestHasStake:
    def test_당사자와_주장만_관계된다(self):
        """'권한 없음'과 '이미 수락함'을 가르는 데 쓴다."""
        app = _app(user_at=AT)
        assert has_stake(app, _APPLICANT, actor_is_owner=False) is True
        assert has_stake(app, _OUTSIDER, actor_is_owner=True) is True
        assert has_stake(app, _OUTSIDER, actor_is_owner=False) is False


class TestConfirmed:
    def test_둘_다_차야_확정이다(self):
        assert _app(user_at=AT).is_confirmed is False
        assert _app(team_at=AT).is_confirmed is False
        assert _app(team_at=AT, user_at=AT).is_confirmed is True

    def test_시작한_쪽을_시각이_말해_준다(self):
        assert _app(team_at=AT).started_by_team is True
        assert _app(user_at=AT).started_by_team is False
