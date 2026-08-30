"""비밀번호 변경을 실제 PostgreSQL 로 확인한다. 5장 SEC-002·SEC-004.

**SEC-004 의 확인 방법 그대로다** — "비밀번호 변경 후 옛 토큰으로 `GET /me` → 401".
스텁은 저장하지 않으므로 이 검사는 여기서만 성립한다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

OLD = "supersub2026"
NEW = "new-password-2026"


@pytest.fixture
def account(db_client, db_session):
    email = f"pwchange-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": OLD, "nickname": "변경시험"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    login = db_client.post(f"{V1}/auth/login", json={"email": email, "password": OLD})
    assert login.status_code == 200

    yield {
        "email": email,
        "user_id": user_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }

    db_session.rollback()
    db_session.execute(
        text("delete from user_credential where user_id = :u"), {"u": str(user_id)}
    )
    db_session.execute(text('delete from "user" where id = :u'), {"u": str(user_id)})
    db_session.commit()


class TestChangePassword:
    def test_바꾸면_새_비밀번호로_로그인된다(self, db_client, account):
        res = db_client.patch(
            f"{V1}/me/password",
            headers=account["headers"],
            json={"current_password": OLD, "new_password": NEW},
        )
        assert res.status_code == 204

        assert (
            db_client.post(
                f"{V1}/auth/login", json={"email": account["email"], "password": NEW}
            ).status_code
            == 200
        )
        # 옛 비밀번호는 더 이상 통하지 않는다.
        assert (
            db_client.post(
                f"{V1}/auth/login", json={"email": account["email"], "password": OLD}
            ).status_code
            == 401
        )

    def test_바꾸면_옛_토큰이_끊긴다(self, db_client, account):
        """SEC-004 의 확인 방법. 바꿔도 옛 토큰이 살아 있으면 바꾼 의미가 없다."""
        assert db_client.get(f"{V1}/me", headers=account["headers"]).status_code == 200

        db_client.patch(
            f"{V1}/me/password",
            headers=account["headers"],
            json={"current_password": OLD, "new_password": NEW},
        )

        after = db_client.get(f"{V1}/me", headers=account["headers"])
        assert after.status_code == 401
        assert error_code(after) == "INVALID_TOKEN"

    def test_현재_비밀번호가_틀리면_바뀌지_않는다(self, db_client, account):
        """토큰을 훔친 쪽이 비밀번호를 갈아 주인을 밀어내지 못하게 한다."""
        res = db_client.patch(
            f"{V1}/me/password",
            headers=account["headers"],
            json={"current_password": "wrong-password", "new_password": NEW},
        )
        assert res.status_code == 401
        assert error_code(res) == "INVALID_CREDENTIALS"

        # 옛 비밀번호가 그대로여야 하고, 쓰던 토큰도 살아 있어야 한다.
        assert (
            db_client.post(
                f"{V1}/auth/login", json={"email": account["email"], "password": OLD}
            ).status_code
            == 200
        )
        assert db_client.get(f"{V1}/me", headers=account["headers"]).status_code == 200

    def test_짧은_새_비밀번호는_거부된다(self, db_client, account):
        res = db_client.patch(
            f"{V1}/me/password",
            headers=account["headers"],
            json={"current_password": OLD, "new_password": "short"},
        )
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

    def test_평문이_저장되지_않는다(self, db_client, db_session, account):
        """SEC-002 — 해시만 보관한다. 변경 경로에서도 같아야 한다."""
        db_client.patch(
            f"{V1}/me/password",
            headers=account["headers"],
            json={"current_password": OLD, "new_password": NEW},
        )

        db_session.rollback()
        stored = db_session.execute(
            text("select password_hash from user_credential where user_id = :u"),
            {"u": str(account["user_id"])},
        ).scalar_one()
        assert stored.startswith("$2b$")
        assert NEW not in stored
