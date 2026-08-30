"""토큰 폐기가 **실제로 토큰을 끊는지** 실제 PostgreSQL 로 확인한다. 5장 SEC-004.

스텁으로는 이것을 볼 수 없다. 계약 테스트의 토큰 버전 판독기는 항상 0 을 돌려주므로
**막히지 않는다** — 그쪽은 응답 형태만 본다. 폐기가 되는지는 여기서만 판별된다.

🔴 이 검사는 `app/core/deps.py` 가 `user.token_version` 을 SQL 로 읽는 부분의
**유일한 방어선**이기도 하다. 컬럼 이름이 바뀌면 파이썬이 잡아 주지 않는다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


@pytest.fixture
def account(db_client, db_session):
    """로그인까지 마친 계정 하나. 끝나면 지운다."""
    email = f"revoke-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "폐기시험"},
    )
    assert signup.status_code == 201, signup.text
    user_id = uuid.UUID(signup.json()["id"])

    login = db_client.post(f"{V1}/auth/login", json={"email": email, "password": PASSWORD})
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


class TestRevocation:
    def test_폐기하면_옛_토큰이_즉시_막힌다(self, db_client, account):
        """SEC-004 의 핵심. **발급된 토큰을 서버가 끊을 수 있어야 한다.**"""
        before = db_client.get(f"{V1}/me", headers=account["headers"])
        assert before.status_code == 200

        logout = db_client.post(f"{V1}/auth/logout-all", headers=account["headers"])
        assert logout.status_code == 204

        after = db_client.get(f"{V1}/me", headers=account["headers"])
        assert after.status_code == 401
        # 클라이언트가 할 일은 "토큰 버리고 재로그인" 이다 — UNAUTHORIZED 가 아니다.
        assert error_code(after) == "INVALID_TOKEN"

    def test_다시_로그인하면_새_토큰은_통한다(self, db_client, account):
        """폐기가 계정을 잠그는 것이 아님을 확인한다. 잠금은 쓰지 않기로 했다(SEC-009)."""
        db_client.post(f"{V1}/auth/logout-all", headers=account["headers"])

        again = db_client.post(
            f"{V1}/auth/login", json={"email": account["email"], "password": PASSWORD}
        )
        assert again.status_code == 200

        fresh = {"Authorization": f"Bearer {again.json()['access_token']}"}
        assert db_client.get(f"{V1}/me", headers=fresh).status_code == 200

    def test_폐기는_그_사람의_토큰만_끊는다(self, db_client, db_session, account):
        """남의 세션까지 끊기면 폐기가 아니라 사고다."""
        other_email = f"other-{uuid.uuid4().hex[:12]}@super-sub.example"
        signup = db_client.post(
            f"{V1}/auth/signup",
            json={"email": other_email, "password": PASSWORD, "nickname": "구경꾼"},
        )
        assert signup.status_code == 201
        other_id = uuid.UUID(signup.json()["id"])
        login = db_client.post(
            f"{V1}/auth/login", json={"email": other_email, "password": PASSWORD}
        )
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        try:
            db_client.post(f"{V1}/auth/logout-all", headers=account["headers"])

            assert db_client.get(f"{V1}/me", headers=other_headers).status_code == 200
        finally:
            db_session.rollback()
            db_session.execute(
                text("delete from user_credential where user_id = :u"),
                {"u": str(other_id)},
            )
            db_session.execute(
                text('delete from "user" where id = :u'), {"u": str(other_id)}
            )
            db_session.commit()

    def test_버전이_실제로_올라간다(self, db_client, db_session, account):
        """대조의 근거가 되는 값이다. 안 올라가면 위 검사들이 우연히 통과한 것이다."""
        db_client.post(f"{V1}/auth/logout-all", headers=account["headers"])

        db_session.rollback()  # 다른 트랜잭션이 커밋한 값을 읽는다
        version = db_session.execute(
            text('select token_version from "user" where id = :u'),
            {"u": str(account["user_id"])},
        ).scalar_one()
        assert version == 1
