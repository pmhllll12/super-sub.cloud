"""`PATCH /me` 를 실제 PostgreSQL 에 대고 확인한다.

스텁은 "응답이 바뀐 값을 담는가"까지만 답한다. **정말 저장됐는지는 여기서만 보인다** —
돌려주는 값만 바꾸고 저장을 빠뜨리면 스텁 테스트는 통과하고 화면은 새로고침에
옛 이름으로 돌아간다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.user.adapter.outbound.orm.user_orm import UserOrm
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


@pytest.fixture
def account(db_client, db_session):
    """가입해서 토큰까지 받아 둔 계정. 끝나면 지운다."""
    email = f"patch-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": "원래이름"},
    )
    assert signup.status_code == 201, signup.text

    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text

    yield {
        "email": email,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }

    db_session.execute(text('delete from "user" where email = :e'), {"e": email})
    db_session.commit()


class TestUpdateMePersists:
    def test_DB_에_실제로_반영된다(self, db_client, db_session, account):
        res = db_client.patch(
            f"{V1}/me", json={"nickname": "바뀐이름"}, headers=account["headers"]
        )
        assert res.status_code == 200, res.text

        row = db_session.execute(
            select(UserOrm).where(UserOrm.email == account["email"])
        ).scalar_one()
        assert row.nickname == "바뀐이름"

    def test_다시_조회해도_바뀐_이름이다(self, db_client, account):
        """응답만 바꾸고 저장을 빠뜨리는 실수를 여기서 잡는다."""
        db_client.patch(
            f"{V1}/me", json={"nickname": "바뀐이름"}, headers=account["headers"]
        )
        me = db_client.get(f"{V1}/me", headers=account["headers"])
        assert me.status_code == 200
        assert me.json()["nickname"] == "바뀐이름"

    def test_이메일과_가입시각은_안_바뀐다(self, db_client, db_session, account):
        before = db_client.get(f"{V1}/me", headers=account["headers"]).json()
        db_client.patch(
            f"{V1}/me", json={"nickname": "바뀐이름"}, headers=account["headers"]
        )
        after = db_client.get(f"{V1}/me", headers=account["headers"]).json()

        assert after["email"] == before["email"]
        assert after["created_at"] == before["created_at"]
        assert after["id"] == before["id"]

    def test_길이가_안_맞으면_저장되지_않는다(self, db_client, db_session, account):
        res = db_client.patch(
            f"{V1}/me", json={"nickname": "가" * 21}, headers=account["headers"]
        )
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"

        row = db_session.execute(
            select(UserOrm).where(UserOrm.email == account["email"])
        ).scalar_one()
        assert row.nickname == "원래이름", "검증에 걸렸는데 저장됐다"
