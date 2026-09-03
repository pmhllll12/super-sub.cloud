"""card/domain/rules/squad_rules.py — 권한 판단. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from app.card.domain.rules.squad_rules import OWNER_ROLE, can_manage, can_read


class TestCanManage:
    def test_주장은_관리할_수_있다(self):
        assert can_manage(OWNER_ROLE)

    def test_구성원은_관리할_수_없다(self):
        """스쿼드는 공개 슬러그로 밖에 보이는 팀의 얼굴이다."""
        assert not can_manage("member")

    def test_소속이_아니면_관리할_수_없다(self):
        assert not can_manage(None)


class TestCanRead:
    def test_소속이면_볼_수_있다(self):
        assert can_read(OWNER_ROLE)
        assert can_read("member")

    def test_소속이_아니면_볼_수_없다(self):
        """팀 id 로 남의 팀 구성을 훑는 것을 막는 자리다."""
        assert not can_read(None)
