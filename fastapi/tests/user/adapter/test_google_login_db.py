"""구글 로그인을 **실제 PostgreSQL** 에 대고 확인한다.

구글에는 붙지 않는다 — 신원 확인만 가짜로 끼우고(`get_identity_verifier` 오버라이드)
그 뒤의 저장·조회는 전부 진짜다. 스텁이 답할 수 없는 것을 본다:
정말 `user_identity` 행이 생기는가, 두 번째 로그인이 같은 사용자를 쓰는가.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.main import app
from app.user.adapter.outbound.orm.user_credential_orm import UserCredentialOrm
from app.user.adapter.outbound.orm.user_identity_orm import UserIdentityOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.identity_provider_port import (
    IdentityProviderPort,
)
from app.user.dependencies.identity_verifier_provider import get_identity_verifier
from app.user.domain.value_objects.external_identity_vo import ExternalIdentity
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db


class _FixedVerifier(IdentityProviderPort):
    def __init__(self, identity: ExternalIdentity) -> None:
        self._identity = identity

    def verify(self, id_token: str) -> ExternalIdentity:
        return self._identity


@pytest.fixture
def google(db_session):
    """가짜 신원을 끼운다. 이메일·subject 는 테스트마다 새로 만들고 끝나면 지운다."""
    email = f"gtest-{uuid.uuid4().hex[:12]}@super-sub.example"
    subject = f"sub-{uuid.uuid4().hex[:12]}"

    def use(**kw):
        base = dict(
            provider="google",
            subject=subject,
            email=email,
            email_verified=True,
            display_name="구글사람",
        )
        base.update(kw)
        app.dependency_overrides[get_identity_verifier] = lambda: _FixedVerifier(
            ExternalIdentity(**base)
        )
        return base

    use.email = email          # type: ignore[attr-defined]
    use.subject = subject      # type: ignore[attr-defined]
    yield use

    app.dependency_overrides.pop(get_identity_verifier, None)
    db_session.execute(text('delete from "user" where email = :e'), {"e": email})
    db_session.commit()


def _login(client):
    return client.post(f"{V1}/auth/google", json={"id_token": "가짜"})


class TestFirstGoogleLogin:
    def test_처음이면_user_와_user_identity_가_함께_생긴다(
        self, db_client, db_session, google
    ):
        google()
        res = _login(db_client)
        assert res.status_code == 200, res.text
        assert res.json()["access_token"].count(".") == 2

        user = db_session.execute(
            select(UserOrm).where(UserOrm.email == google.email)
        ).scalar_one()

        link = db_session.execute(
            select(UserIdentityOrm).where(UserIdentityOrm.user_id == user.id)
        ).scalar_one()
        assert link.provider == "google"
        assert link.subject == google.subject

    def test_비밀번호_자격증명은_만들지_않는다(self, db_client, db_session, google):
        """구글로 들어온 계정은 비밀번호가 없다 — 빈 해시를 넣으면 안 된다."""
        google()
        _login(db_client)

        user = db_session.execute(
            select(UserOrm).where(UserOrm.email == google.email)
        ).scalar_one()
        credential = db_session.execute(
            select(UserCredentialOrm).where(UserCredentialOrm.user_id == user.id)
        ).scalar_one_or_none()
        assert credential is None

    def test_그_토큰으로_me_가_된다(self, db_client, google):
        google()
        token = _login(db_client).json()["access_token"]
        me = db_client.get(f"{V1}/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
        assert me.json()["email"] == google.email
        assert me.json()["nickname"] == "구글사람"


class TestSecondGoogleLogin:
    def test_두_번째_로그인은_같은_사용자를_쓴다(
        self, db_client, db_session, google
    ):
        google()
        first = _login(db_client)
        second = _login(db_client)
        assert first.status_code == second.status_code == 200

        rows = db_session.execute(
            select(UserOrm).where(UserOrm.email == google.email)
        ).scalars().all()
        assert len(rows) == 1, "두 번째 로그인이 계정을 또 만들었다"

        links = db_session.execute(
            select(UserIdentityOrm).where(UserIdentityOrm.user_id == rows[0].id)
        ).scalars().all()
        assert len(links) == 1


class TestEmailCollisionAgainstDb:
    def test_비밀번호로_가입한_계정에_확인된_이메일이면_연결된다(
        self, db_client, db_session, google
    ):
        google()
        signup = db_client.post(
            f"{V1}/auth/signup",
            json={
                "email": google.email,
                "password": "supersub2026",
                "nickname": "원래사람",
            },
        )
        assert signup.status_code == 201

        res = _login(db_client)
        assert res.status_code == 200, res.text

        user = db_session.execute(
            select(UserOrm).where(UserOrm.email == google.email)
        ).scalar_one()
        assert str(user.id) == signup.json()["id"], "다른 계정이 만들어졌다"
        # 닉네임은 원래 것을 유지한다 — 구글 표시 이름으로 덮어쓰지 않는다.
        assert user.nickname == "원래사람"

    def test_확인되지_않은_이메일이면_409(self, db_client, google):
        google(email_verified=False)
        db_client.post(
            f"{V1}/auth/signup",
            json={
                "email": google.email,
                "password": "supersub2026",
                "nickname": "원래사람",
            },
        )
        res = _login(db_client)
        assert res.status_code == 409
        assert error_code(res) == "EMAIL_ALREADY_EXISTS"
