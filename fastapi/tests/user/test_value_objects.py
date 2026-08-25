"""user/domain/value_objects.py"""

from app.user.domain.value_objects import (
    MIN_PASSWORD_LENGTH,
    Email,
    Nickname,
    Password,
)


class TestEmail:
    def test_대소문자만_다른_주소는_같은_값이_된다(self):
        # user.email 에 유일 제약이 있다(부록 D.7). 정규화하지 않으면
        # Demo@... 와 demo@... 가 별개 계정이 된다.
        assert Email.of("Demo@Super-Sub.example") == Email.of("demo@super-sub.example")

    def test_앞뒤_공백을_지운다(self):
        assert Email.of("  demo@example.com \n").value == "demo@example.com"

    def test_문자열로_쓰면_정규화된_값이_나온다(self):
        assert str(Email.of("A@B.COM")) == "a@b.com"


class TestNickname:
    def test_앞뒤_공백을_지운다(self):
        assert Nickname.of("  홍길동 ").value == "홍길동"


class TestPassword:
    def test_8자_미만은_거부한다(self):
        assert not Password("a" * (MIN_PASSWORD_LENGTH - 1)).is_acceptable()

    def test_8자면_통과한다(self):
        assert Password("a" * MIN_PASSWORD_LENGTH).is_acceptable()

    def test_대문자나_특수문자를_요구하지_않는다(self):
        # 예측 가능한 패턴으로 사용자를 몰기만 한다. 계약 문서 2장.
        assert Password("supersub2026").is_acceptable()
