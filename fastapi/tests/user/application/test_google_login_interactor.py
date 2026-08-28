"""구글 로그인 인터랙터. DB도 네트워크도 없이 세 갈래를 전부 눌러 본다.

인터랙터는 구글을 모른다 — `IdentityProviderPort` 가 확인해 준 신원만 받는다.
그래서 가짜 제공자 하나면 모든 경로를 시험할 수 있다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import verify_access_token
from app.user.application.dtos.login_dto import GoogleLoginCommand
from app.user.application.ports.output.identity_provider_port import (
    IdentityProviderPort,
)
from app.user.application.ports.output.user_port import UserPort
from app.user.application.use_cases.google_login_interactor import (
    GoogleLoginInteractor,
)
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.external_identity_vo import ExternalIdentity
from app.user.domain.value_objects.nickname_vo import MAX_NICKNAME_LENGTH, Nickname
from app.user.domain.value_objects.password_vo import Password

if not settings.jwt_secret:
    settings.jwt_secret = "test-only-secret-not-for-deploy"

EXISTING_ID = UUID("3f1c9d2e-0a44-4b7c-9e11-2b5d8c6a1f30")
EXISTING_EMAIL = "already@super-sub.example"


def identity(**kw) -> ExternalIdentity:
    base = dict(
        provider="google",
        subject="google-sub-1",
        email="newcomer@super-sub.example",
        email_verified=True,
        display_name="새사람",
    )
    base.update(kw)
    return ExternalIdentity(**base)


class FakeProvider(IdentityProviderPort):
    def __init__(self, result: ExternalIdentity) -> None:
        self._result = result

    def verify(self, id_token: str) -> ExternalIdentity:
        return self._result


class FakeRepo(UserPort):
    """이메일로 찾히는 기존 사용자를 넣을지 말지로 갈래를 만든다."""

    def __init__(self, *, existing_email: str | None = None) -> None:
        self.existing = (
            UserEntity(
                id=EXISTING_ID,
                email=Email.of(existing_email),
                nickname=Nickname.of("기존사람"),
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            )
            if existing_email
            else None
        )
        self.identities: dict[tuple[str, str], UserEntity] = {}
        self.created: list[UserEntity] = []
        self.linked: list[tuple[UUID, str, str]] = []

    def find_by_identity(self, provider: str, subject: str) -> UserEntity | None:
        return self.identities.get((provider, subject))

    def find_by_email(self, email: Email) -> UserEntity | None:
        if self.existing and self.existing.email == email:
            return self.existing
        return None

    def link_identity(self, user_id: UUID, provider: str, subject: str) -> None:
        self.linked.append((user_id, provider, subject))

    def create_with_identity(
        self, user: UserEntity, provider: str, subject: str
    ) -> None:
        self.created.append(user)
        self.identities[(provider, subject)] = user

    # --- 아래는 이 유스케이스가 쓰지 않는다 -------------------------------
    def email_exists(self, email: Email) -> bool: ...
    def create(self, user: UserEntity, password: Password) -> None: ...
    def find_by_credentials(self, email, password): ...
    def get(self, user_id: UUID) -> UserEntity | None: ...
    def update_nickname(self, user_id: UUID, nickname: Nickname) -> None: ...
    def bump_token_version(self, user_id: UUID) -> None: ...
    def list_memberships(self, user_id: UUID) -> list[MembershipEntity]: ...


def run(repo: FakeRepo, ident: ExternalIdentity):
    return GoogleLoginInteractor(repo, FakeProvider(ident))(
        GoogleLoginCommand(id_token="아무거나")
    )


class TestFirstTime:
    def test_처음_온_사람이면_계정을_만들고_토큰을_준다(self):
        repo = FakeRepo()
        result = run(repo, identity())

        assert len(repo.created) == 1
        assert str(repo.created[0].email) == "newcomer@super-sub.example"
        token = verify_access_token(f"Bearer {result.access_token}")
        assert token.user_id == repo.created[0].id

    def test_표시_이름이_상한을_넘으면_자른다(self):
        """자르지 않으면 저장 시점에 터진다 — 사용자가 고칠 수 없는 실패다."""
        repo = FakeRepo()
        run(repo, identity(display_name="가" * 50))
        assert len(str(repo.created[0].nickname)) == MAX_NICKNAME_LENGTH

    def test_표시_이름이_없으면_이메일_앞부분을_쓴다(self):
        repo = FakeRepo()
        run(repo, identity(display_name="   "))
        assert str(repo.created[0].nickname) == "newcomer"


class TestAlreadyLinked:
    def test_이미_연결된_신원이면_계정을_만들지_않는다(self):
        repo = FakeRepo()
        run(repo, identity())          # 1회차 — 생성
        run(repo, identity())          # 2회차 — 재사용
        assert len(repo.created) == 1
        assert repo.linked == []


class TestEmailCollision:
    def test_확인된_이메일이면_기존_계정에_연결한다(self):
        repo = FakeRepo(existing_email=EXISTING_EMAIL)
        result = run(repo, identity(email=EXISTING_EMAIL, email_verified=True))

        assert repo.created == []
        assert repo.linked == [(EXISTING_ID, "google", "google-sub-1")]
        assert verify_access_token(f"Bearer {result.access_token}").user_id == EXISTING_ID

    def test_확인되지_않은_이메일이면_연결하지_않는다(self):
        """🔴 연결해 주면 아무 이메일이나 적어 남의 계정을 가져갈 수 있다."""
        repo = FakeRepo(existing_email=EXISTING_EMAIL)
        with pytest.raises(ApiError) as exc:
            run(repo, identity(email=EXISTING_EMAIL, email_verified=False))

        assert exc.value.status_code == 409
        assert exc.value.code == "EMAIL_ALREADY_EXISTS"
        assert repo.linked == []

    def test_대소문자만_달라도_같은_계정으로_본다(self):
        repo = FakeRepo(existing_email=EXISTING_EMAIL)
        run(repo, identity(email=EXISTING_EMAIL.upper(), email_verified=True))
        assert repo.linked and repo.created == []


class TestBadIdentity:
    def test_이메일이_없으면_422(self):
        repo = FakeRepo()
        with pytest.raises(ApiError) as exc:
            run(repo, identity(email=""))
        assert exc.value.status_code == 422
        assert exc.value.code == "GOOGLE_EMAIL_MISSING"
