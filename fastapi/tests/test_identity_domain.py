"""사용자·팀 도메인 규칙 — HTTP도 DB도 띄우지 않는다."""

from datetime import datetime, timezone
from uuid import uuid4

from app.identity.domain import (
    MIN_PASSWORD_LENGTH,
    Membership,
    active_memberships,
    is_password_acceptable,
    normalize_email,
)


def _membership(left_at: datetime | None) -> Membership:
    return Membership(
        team_id=uuid4(),
        name="번개FC",
        region="서울 강남",
        sport_code="futsal",
        role="member",
        joined_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        left_at=left_at,
    )


class TestNormalizeEmail:
    def test_대소문자만_다른_주소는_같은_값이_된다(self):
        # user.email 에 유일 제약이 있다(부록 D.7). 정규화하지 않으면
        # Demo@... 와 demo@... 가 별개 계정이 된다.
        assert normalize_email("Demo@Super-Sub.example") == "demo@super-sub.example"

    def test_앞뒤_공백을_지운다(self):
        assert normalize_email("  demo@example.com \n") == "demo@example.com"


class TestActiveMemberships:
    def test_탈퇴한_소속을_걸러낸다(self):
        # team_member 는 탈퇴해도 행이 남는다 — 경기·평가 이력이 참조하므로
        # left_at 으로 소프트 삭제한다. 거르지 않으면 나간 팀이 내 정보에 나온다.
        rows = [_membership(None), _membership(datetime(2026, 6, 30, tzinfo=timezone.utc))]

        result = active_memberships(rows)

        assert len(result) == 1
        assert result[0].left_at is None

    def test_전부_탈퇴했으면_빈_목록이다(self):
        rows = [_membership(datetime(2026, 6, 30, tzinfo=timezone.utc))]
        assert active_memberships(rows) == []

    def test_원본을_바꾸지_않는다(self):
        rows = [_membership(None), _membership(datetime(2026, 6, 30, tzinfo=timezone.utc))]
        active_memberships(rows)
        assert len(rows) == 2


class TestPasswordPolicy:
    def test_8자_미만은_거부한다(self):
        assert not is_password_acceptable("a" * (MIN_PASSWORD_LENGTH - 1))

    def test_8자면_통과한다(self):
        assert is_password_acceptable("a" * MIN_PASSWORD_LENGTH)

    def test_대문자나_특수문자를_요구하지_않는다(self):
        # 예측 가능한 패턴으로 사용자를 몰기만 한다. 계약 문서 2장.
        assert is_password_acceptable("supersub2026")
