"""user/application/use_cases/ — 가짜 저장소를 끼워서 돌린다.

**출력 포트를 둔 값이 여기서 나온다.** DB도 HTTP도 없이 인터랙터만 검증한다.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.errors import ApiError
from app.core.security import verify_access_token
from app.user.application.dtos.login_dto import LoginCommand
from app.user.application.dtos.me_dto import MeQuery, UpdateMeCommand
from app.user.application.dtos.signup_dto import SignupCommand
from app.user.application.ports.output.user_port import UserPort
from app.user.application.use_cases.login_interactor import LoginInteractor
from app.user.application.use_cases.me_interactor import MeInteractor
from app.user.application.use_cases.update_me_interactor import UpdateMeInteractor
from app.user.application.use_cases.signup_interactor import SignupInteractor
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname
from app.user.domain.value_objects.password_vo import Password

_USER_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")
_EMAIL = "demo@super-sub.example"
_PASSWORD = "supersub2026"


def _membership(name: str, left_at: datetime | None) -> MembershipEntity:
    return MembershipEntity(
        team_id=uuid4(),
        name=name,
        region="서울",
        sport_code="futsal",
        role="member",
        joined_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        left_at=left_at,
    )


class FakeUserRepository(UserPort):
    """포트만 만족하면 된다. 실제 저장소 없이 인터랙터를 돌릴 수 있다."""

    def __init__(self, memberships: list[MembershipEntity] | None = None) -> None:
        self.user = UserEntity(
            id=_USER_ID,
            email=Email.of(_EMAIL),
            nickname=Nickname.of("홍길동"),
            created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
        )
        self.memberships = memberships or []
        # 저장된 것을 눈으로 확인할 수 있게 남긴다. 인터랙터가 실제로 저장을
        # 호출하는지는 이 목록으로 검사한다.
        self.created: list[tuple[UserEntity, Password]] = []
        # 외부 신원 쪽도 같은 방식으로 남긴다.
        self.identities: dict[tuple[str, str], UserEntity] = {}
        self.linked: list[tuple[UUID, str, str]] = []
        self.renamed: list[tuple[UUID, Nickname]] = []

    def email_exists(self, email: Email) -> bool:
        return email == Email.of(_EMAIL)

    def create(self, user: UserEntity, password: Password) -> None:
        self.created.append((user, password))

    def find_by_credentials(
        self, email: Email, password: Password
    ) -> UserEntity | None:
        if email == Email.of(_EMAIL) and password.value == _PASSWORD:
            return self.user
        return None

    def find_by_identity(self, provider: str, subject: str) -> UserEntity | None:
        return self.identities.get((provider, subject))

    def find_by_email(self, email: Email) -> UserEntity | None:
        return self.user if email == Email.of(_EMAIL) else None

    def link_identity(self, user_id: UUID, provider: str, subject: str) -> None:
        self.linked.append((user_id, provider, subject))
        self.identities[(provider, subject)] = self.user

    def create_with_identity(
        self, user: UserEntity, provider: str, subject: str
    ) -> None:
        self.created.append((user, Password("")))
        self.identities[(provider, subject)] = user

    def get(self, user_id: UUID) -> UserEntity | None:
        return self.user if user_id == _USER_ID else None

    def update_nickname(self, user_id: UUID, nickname: Nickname) -> None:
        self.renamed.append((user_id, nickname))

    def list_memberships(self, user_id: UUID) -> list[MembershipEntity]:
        return list(self.memberships)


class TestSignupInteractor:
    def test_이메일을_정규화해서_돌려준다(self):
        result = SignupInteractor(FakeUserRepository())(
            SignupCommand(email="  NEW@Example.COM ", password="password123", nickname="  새사람 ")
        )
        assert result.email == "new@example.com"
        assert result.nickname == "새사람"

    def test_결과는_원시_타입만_담는다(self):
        # DTO 에 값 객체가 새어 나가면 라우터가 도메인을 알게 된다.
        result = SignupInteractor(FakeUserRepository())(
            SignupCommand(email="new@example.com", password="password123", nickname="새사람")
        )
        assert isinstance(result.email, str)
        assert isinstance(result.nickname, str)

    def test_중복이면_409(self):
        with pytest.raises(ApiError) as exc:
            SignupInteractor(FakeUserRepository())(
                SignupCommand(email=_EMAIL, password="password123", nickname="홍길동")
            )
        assert exc.value.status_code == 409
        assert exc.value.code == "EMAIL_ALREADY_EXISTS"

    def test_대소문자가_달라도_중복으로_잡는다(self):
        # 정규화가 중복 검사 앞에 오는지 확인한다.
        with pytest.raises(ApiError):
            SignupInteractor(FakeUserRepository())(
                SignupCommand(email=_EMAIL.upper(), password="password123", nickname="홍길동")
            )


class TestLoginInteractor:
    def test_토큰을_발급한다(self):
        result = LoginInteractor(FakeUserRepository())(
            LoginCommand(email=_EMAIL, password=_PASSWORD)
        )
        assert result.token_type == "bearer"
        assert result.expires_in == 7 * 24 * 60 * 60

    def test_발급한_토큰이_그_사용자를_가리킨다(self):
        result = LoginInteractor(FakeUserRepository())(
            LoginCommand(email=_EMAIL, password=_PASSWORD)
        )
        assert verify_access_token(f"Bearer {result.access_token}") == _USER_ID

    @pytest.mark.parametrize(
        ("email", "password"),
        [(_EMAIL, "wrong-password"), ("nobody@example.com", _PASSWORD)],
        ids=["비밀번호틀림", "없는계정"],
    )
    def test_실패는_같은_code_를_준다(self, email, password):
        # 구분하면 가입 여부가 새어 나간다.
        with pytest.raises(ApiError) as exc:
            LoginInteractor(FakeUserRepository())(
                LoginCommand(email=email, password=password)
            )
        assert exc.value.code == "INVALID_CREDENTIALS"


class TestMeInteractor:
    def test_탈퇴한_팀은_안_나온다(self):
        repo = FakeUserRepository(
            [
                _membership("번개FC", None),
                _membership("옛날FC", datetime(2026, 6, 30, tzinfo=timezone.utc)),
            ]
        )
        result = MeInteractor(repo)(MeQuery(user_id=_USER_ID))
        assert [t.name for t in result.teams] == ["번개FC"]

    def test_없는_사용자면_INVALID_TOKEN(self):
        # 토큰은 유효한데 사용자가 없는 경우 — 탈퇴했거나 위조된 id 다.
        with pytest.raises(ApiError) as exc:
            MeInteractor(FakeUserRepository())(MeQuery(user_id=uuid4()))
        assert exc.value.code == "INVALID_TOKEN"


class TestUpdateMeInteractor:
    def test_바뀐_닉네임으로_돌려준다(self):
        repo = FakeUserRepository()
        result = UpdateMeInteractor(repo)(
            UpdateMeCommand(user_id=_USER_ID, nickname="새이름")
        )
        assert result.nickname == "새이름"

    def test_저장소에_저장을_요청한다(self):
        """돌려주는 값만 바꾸고 저장을 안 하면 새로고침에 되돌아간다."""
        repo = FakeUserRepository()
        UpdateMeInteractor(repo)(
            UpdateMeCommand(user_id=_USER_ID, nickname="새이름")
        )
        assert [str(n) for _, n in repo.renamed] == ["새이름"]

    def test_앞뒤_공백은_값_객체가_정규화한다(self):
        repo = FakeUserRepository()
        result = UpdateMeInteractor(repo)(
            UpdateMeCommand(user_id=_USER_ID, nickname="  새이름  ")
        )
        assert result.nickname == "새이름"
        assert str(repo.renamed[0][1]) == "새이름", "저장되는 값도 정규화돼야 한다"

    def test_없는_사용자면_INVALID_TOKEN(self):
        """조회(`MeInteractor`)와 같은 판단이어야 화면 동작이 갈리지 않는다."""
        repo = FakeUserRepository()
        with pytest.raises(ApiError) as exc:
            UpdateMeInteractor(repo)(
                UpdateMeCommand(user_id=uuid4(), nickname="새이름")
            )
        assert exc.value.status_code == 401
        assert exc.value.code == "INVALID_TOKEN"
        assert repo.renamed == [], "없는 사용자인데 저장을 시도했다"

    def test_teams_는_조회와_같게_나온다(self):
        """수정 응답만 형태가 다르면 클라이언트가 파서를 두 벌 든다."""
        repo = FakeUserRepository(
            [
                _membership("번개FC", None),
                _membership("옛날FC", datetime(2026, 6, 30, tzinfo=timezone.utc)),
            ]
        )
        result = UpdateMeInteractor(repo)(
            UpdateMeCommand(user_id=_USER_ID, nickname="새이름")
        )
        assert [t.name for t in result.teams] == ["번개FC"]
