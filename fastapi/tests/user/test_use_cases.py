"""user/application/use_cases.py

**가짜 저장소를 끼워서 돌린다.** 출력 포트를 둔 값이 여기서 나온다 — DB도 HTTP도
없이 유스케이스만 검증한다.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.errors import ApiError
from app.user.application.use_cases import LoginUseCase, MeUseCase, SignupUseCase
from app.user.domain.entities import Membership, User
from app.user.domain.value_objects import Email, Nickname, Password

_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")
_EMAIL = "demo@super-sub.example"
_PASSWORD = "supersub2026"


def _membership(name: str, left_at: datetime | None) -> Membership:
    return Membership(
        team_id=uuid4(),
        name=name,
        region="서울",
        sport_code="futsal",
        role="member",
        joined_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        left_at=left_at,
    )


class FakeUserRepository:
    """포트만 만족하면 된다. 실제 저장소가 없어도 유스케이스를 돌릴 수 있다."""

    def __init__(self, memberships: list[Membership] | None = None) -> None:
        self.user = User(
            id=_USER_ID,
            email=Email.of(_EMAIL),
            nickname=Nickname.of("홍길동"),
            created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
        )
        self.memberships = memberships or []

    def email_exists(self, email: Email) -> bool:
        return email == Email.of(_EMAIL)

    def find_by_credentials(self, email: Email, password: Password) -> User | None:
        if email == Email.of(_EMAIL) and password.value == _PASSWORD:
            return self.user
        return None

    def get(self, user_id: UUID) -> User | None:
        return self.user if user_id == _USER_ID else None

    def list_memberships(self, user_id: UUID) -> list[Membership]:
        return list(self.memberships)


class TestSignup:
    def test_이메일을_정규화해서_돌려준다(self):
        user = SignupUseCase(FakeUserRepository())(
            "  NEW@Example.COM ", "password123", "  새사람 "
        )
        assert str(user.email) == "new@example.com"
        assert str(user.nickname) == "새사람"

    def test_중복이면_409(self):
        with pytest.raises(ApiError) as exc:
            SignupUseCase(FakeUserRepository())(_EMAIL, "password123", "홍길동")
        assert exc.value.status_code == 409
        assert exc.value.code == "EMAIL_ALREADY_EXISTS"

    def test_대소문자가_달라도_중복으로_잡는다(self):
        # 정규화가 중복 검사 앞에 오는지 확인한다.
        with pytest.raises(ApiError):
            SignupUseCase(FakeUserRepository())(_EMAIL.upper(), "password123", "홍길동")


class TestLogin:
    def test_토큰을_발급한다(self):
        issued = LoginUseCase(FakeUserRepository())(_EMAIL, _PASSWORD)
        assert issued.access_token
        assert issued.expires_in == 7 * 24 * 60 * 60

    def test_발급한_토큰이_그_사용자를_가리킨다(self):
        from app.security import verify_access_token

        issued = LoginUseCase(FakeUserRepository())(_EMAIL, _PASSWORD)
        assert verify_access_token(f"Bearer {issued.access_token}") == _USER_ID

    @pytest.mark.parametrize(
        ("email", "password"),
        [(_EMAIL, "wrong-password"), ("nobody@example.com", _PASSWORD)],
        ids=["비밀번호틀림", "없는계정"],
    )
    def test_실패는_같은_code_를_준다(self, email, password):
        # 구분하면 가입 여부가 새어 나간다.
        with pytest.raises(ApiError) as exc:
            LoginUseCase(FakeUserRepository())(email, password)
        assert exc.value.code == "INVALID_CREDENTIALS"


class TestMe:
    def test_탈퇴한_팀은_안_나온다(self):
        repo = FakeUserRepository(
            [
                _membership("번개FC", None),
                _membership("옛날FC", datetime(2026, 6, 30, tzinfo=timezone.utc)),
            ]
        )
        _, memberships = MeUseCase(repo)(_USER_ID)
        assert [m.name for m in memberships] == ["번개FC"]

    def test_없는_사용자면_INVALID_TOKEN(self):
        # 토큰은 유효한데 사용자가 없는 경우 — 탈퇴했거나 위조된 id 다.
        with pytest.raises(ApiError) as exc:
            MeUseCase(FakeUserRepository())(uuid4())
        assert exc.value.code == "INVALID_TOKEN"
