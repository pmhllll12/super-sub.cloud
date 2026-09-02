"""user/domain/rules/team_rules.py — 권한 규칙만 따로 본다.

**아무것도 안 띄운다.** 규칙이 인터랙터 안에 흩어져 있으면 이런 검사를 쓸 수 없다.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.user.domain.entities.team_entity import TeamMemberEntity
from app.user.domain.rules.team_rules import (
    can_add_member,
    can_remove_member,
    is_last_owner,
)
from app.user.domain.value_objects.team_role_vo import TeamRole

_ME = uuid4()
_OTHER = uuid4()


def _member(user_id, role):
    return TeamMemberEntity(
        user_id=user_id,
        nickname="아무개",
        role=role,
        joined_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


class TestCanAddMember:
    def test_자기_자신은_소속이_아니어도_넣을_수_있다(self):
        """가입이다. 이때 역할은 None 이다 — 아직 팀에 없으니까."""
        assert can_add_member(None, adding_self=True) is True

    def test_남을_넣는_것은_주장만(self):
        assert can_add_member(TeamRole.OWNER, adding_self=False) is True
        assert can_add_member(TeamRole.MEMBER, adding_self=False) is False
        assert can_add_member(None, adding_self=False) is False


class TestCanRemoveMember:
    def test_본인은_언제나_나갈_수_있다(self):
        assert can_remove_member(_ME, _ME, TeamRole.MEMBER) is True

    def test_남을_빼는_것은_주장만(self):
        assert can_remove_member(_ME, _OTHER, TeamRole.OWNER) is True
        assert can_remove_member(_ME, _OTHER, TeamRole.MEMBER) is False
        assert can_remove_member(_ME, _OTHER, None) is False


class TestIsLastOwner:
    def test_주장이_하나면_그_사람이_마지막이다(self):
        members = [_member(_ME, TeamRole.OWNER), _member(_OTHER, TeamRole.MEMBER)]
        assert is_last_owner(members, _ME) is True

    def test_주장이_둘이면_아니다(self):
        members = [_member(_ME, TeamRole.OWNER), _member(_OTHER, TeamRole.OWNER)]
        assert is_last_owner(members, _ME) is False

    def test_일반_구성원은_해당_없다(self):
        members = [_member(_OTHER, TeamRole.OWNER), _member(_ME, TeamRole.MEMBER)]
        assert is_last_owner(members, _ME) is False
