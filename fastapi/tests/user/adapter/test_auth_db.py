"""실제 PostgreSQL 을 쓰는 가입·로그인 검증.

계약(응답 형태·에러 코드)은 스텁으로 이미 검사한다. **여기서 보는 것은 스텁이
답할 수 없는 것들이다** — 정말 저장되는가, 해시로 저장되는가, 유일 제약이
실제로 409 로 옮겨지는가.

DB 가 없으면 건너뛴다. 띄우는 법은 `.env.example` 참조.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.user.adapter.outbound.orm.user_credential_orm import UserCredentialOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


@pytest.fixture
def fresh_email(db_session):
    """이 테스트만 쓰는 이메일. 끝나면 지운다.

    지우는 것을 `finally` 가 아니라 픽스처 해제에 두는 이유는, 테스트가 실패해도
    반드시 정리되어야 다음 실행이 "이미 있는 이메일"로 오염되지 않기 때문이다.
    """
    email = f"dbtest-{uuid.uuid4().hex[:12]}@super-sub.example"
    yield email
    db_session.execute(text('delete from "user" where email = :e'), {"e": email})
    db_session.commit()


def _signup(client, email: str, nickname: str = "테스터"):
    return client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )


class TestSignupPersists:
    def test_가입하면_user_와_user_credential_이_함께_저장된다(
        self, db_client, db_session, fresh_email
    ):
        res = _signup(db_client, fresh_email)
        assert res.status_code == 201, res.text

        row = db_session.execute(
            select(UserOrm).where(UserOrm.email == fresh_email)
        ).scalar_one()
        assert str(row.id) == res.json()["id"]

        credential = db_session.execute(
            select(UserCredentialOrm).where(UserCredentialOrm.user_id == row.id)
        ).scalar_one()
        assert credential is not None

    def test_비밀번호는_평문으로_저장되지_않는다(
        self, db_client, db_session, fresh_email
    ):
        _signup(db_client, fresh_email)
        credential = db_session.execute(
            select(UserCredentialOrm)
            .join(UserOrm, UserOrm.id == UserCredentialOrm.user_id)
            .where(UserOrm.email == fresh_email)
        ).scalar_one()

        assert PASSWORD not in credential.password_hash
        # bcrypt 해시의 형태. 알고리즘이 바뀌면 이 단언도 같이 바뀌어야 한다.
        assert credential.password_hash.startswith("$2b$")

    def test_대문자로_가입해도_소문자로_저장된다(
        self, db_client, db_session, fresh_email
    ):
        res = _signup(db_client, fresh_email.upper())
        assert res.status_code == 201
        assert res.json()["email"] == fresh_email

        found = db_session.execute(
            select(UserOrm).where(UserOrm.email == fresh_email)
        ).scalar_one_or_none()
        assert found is not None, "DB 에 소문자로 저장되지 않았다"


class TestSignupConflict:
    def test_같은_이메일로_두_번_가입하면_409(self, db_client, fresh_email):
        assert _signup(db_client, fresh_email).status_code == 201
        res = _signup(db_client, fresh_email)
        assert res.status_code == 409
        assert error_code(res) == "EMAIL_ALREADY_EXISTS"

    def test_대소문자만_달라도_중복으로_잡는다(self, db_client, fresh_email):
        """DB 의 유일 제약은 대소문자를 구분한다 — 막는 것은 Email 값 객체다."""
        assert _signup(db_client, fresh_email).status_code == 201
        res = _signup(db_client, fresh_email.upper())
        assert res.status_code == 409
        assert error_code(res) == "EMAIL_ALREADY_EXISTS"


class TestLoginAgainstDb:
    def test_가입한_계정으로_로그인하고_그_토큰으로_me_가_된다(
        self, db_client, fresh_email
    ):
        signup = _signup(db_client, fresh_email, nickname="김테스트")
        assert signup.status_code == 201

        res = db_client.post(
            f"{V1}/auth/login", json={"email": fresh_email, "password": PASSWORD}
        )
        assert res.status_code == 200, res.text
        token = res.json()["access_token"]
        # 서명된 JWT 는 점 두 개로 나뉜다. 옛 스텁 토큰과 형태가 다르다.
        assert token.count(".") == 2

        me = db_client.get(
            f"{V1}/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me.status_code == 200, me.text
        assert me.json()["email"] == fresh_email
        assert me.json()["nickname"] == "김테스트"

    def test_틀린_비밀번호는_401(self, db_client, fresh_email):
        _signup(db_client, fresh_email)
        res = db_client.post(
            f"{V1}/auth/login", json={"email": fresh_email, "password": "wrong-one"}
        )
        assert res.status_code == 401
        assert error_code(res) == "INVALID_CREDENTIALS"

    def test_없는_이메일도_같은_code_다(self, db_client):
        """가입 여부가 새어 나가면 안 된다 — 두 실패가 구분되면 계정 열거가 된다."""
        res = db_client.post(
            f"{V1}/auth/login",
            json={"email": "nobody-here@super-sub.example", "password": PASSWORD},
        )
        assert res.status_code == 401
        assert error_code(res) == "INVALID_CREDENTIALS"
