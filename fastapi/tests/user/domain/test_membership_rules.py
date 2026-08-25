"""user/domain/rules/membership_rules.py"""

from datetime import datetime, timezone
from uuid import uuid4

from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.rules.membership_rules import active_memberships

_LEFT = datetime(2026, 6, 30, tzinfo=timezone.utc)


def _membership(left_at: datetime | None) -> MembershipEntity:
    return MembershipEntity(
        team_id=uuid4(),
        name="번개FC",
        region="서울 강남",
        sport_code="futsal",
        role="member",
        joined_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        left_at=left_at,
    )


class TestActiveMemberships:
    def test_탈퇴한_소속을_걸러낸다(self):
        # team_member 는 탈퇴해도 행이 남는다 — 경기·평가 이력이 참조하므로
        # left_at 으로 소프트 삭제한다. 거르지 않으면 나간 팀이 내 정보에 나온다.
        result = active_memberships([_membership(None), _membership(_LEFT)])

        assert len(result) == 1
        assert result[0].is_active

    def test_전부_탈퇴했으면_빈_목록이다(self):
        assert active_memberships([_membership(_LEFT)]) == []

    def test_원본을_바꾸지_않는다(self):
        rows = [_membership(None), _membership(_LEFT)]
        active_memberships(rows)
        assert len(rows) == 2
