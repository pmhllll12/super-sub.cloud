"""user/adapter/inbound/api/v1/auth_router.py — 계약 문서 2장.

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다.** 이 규칙이 실제로
버그를 잡았다 — 에러 핸들러가 통째로 깨져 모든 실패가 500 이 된 적이 있다.
"""

import pytest

from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)
from tests.conftest import V1, error_code


class TestHealth:
    def test_기동(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        # 카드까지 DB 로 옮긴 뒤로 스텁 경로가 없다(2026-08-26).
        assert res.json()["stub"] is False


class TestLogin:
    def test_성공하면_토큰과_만료를_준다(self, client):
        res = client.post(
            f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert res.status_code == 200
        body = res.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 7 * 24 * 60 * 60
        assert body["access_token"]

    def test_대소문자가_달라도_로그인된다(self, client):
        res = client.post(
            f"{V1}/auth/login",
            json={"email": DEMO_EMAIL.upper(), "password": DEMO_PASSWORD},
        )
        assert res.status_code == 200

    @pytest.mark.parametrize(
        ("email", "password"),
        [(DEMO_EMAIL, "wrong-password"), ("nobody@example.com", "whatever12")],
        ids=["비밀번호틀림", "없는계정"],
    )
    def test_실패는_같은_code_를_준다(self, client, email, password):
        res = client.post(
            f"{V1}/auth/login", json={"email": email, "password": password}
        )
        assert res.status_code == 401
        assert error_code(res) == "INVALID_CREDENTIALS"


class TestSignup:
    def test_새_이메일이면_201(self, client):
        res = client.post(
            f"{V1}/auth/signup",
            json={
                "email": "new@example.com",
                "password": "password123",
                "nickname": "새사람",
            },
        )
        assert res.status_code == 201
        body = res.json()
        assert body["nickname"] == "새사람"
        assert body["email"] == "new@example.com"
        assert "password" not in body

    def test_중복_이메일이면_409(self, client):
        res = client.post(
            f"{V1}/auth/signup",
            json={"email": DEMO_EMAIL, "password": "password123", "nickname": "홍길동"},
        )
        assert res.status_code == 409
        assert error_code(res) == "EMAIL_ALREADY_EXISTS"

    @pytest.mark.parametrize(
        "payload",
        [
            {"email": "a@example.com", "password": "short", "nickname": "짧아"},
            {"email": "not-an-email", "password": "password123", "nickname": "홍길동"},
            {"email": "a@example.com", "password": "password123", "nickname": ""},
            {"email": "a@example.com", "password": "password123", "nickname": "가" * 21},
        ],
        ids=["짧은비밀번호", "잘못된이메일", "빈닉네임", "긴닉네임"],
    )
    def test_검증에_걸리면_422(self, client, payload):
        res = client.post(f"{V1}/auth/signup", json=payload)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"


class TestLogoutAll:
    """폐기가 **실제로 토큰을 끊는지**는 `test_token_revocation_db.py` 가 본다.

    여기서는 계약만 본다 — 인증이 필요한가, 성공하면 무엇을 주는가.
    """

    def test_토큰이_없으면_401(self, client):
        res = client.post(f"{V1}/auth/logout-all")
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    def test_성공하면_204_이고_본문이_없다(self, client, auth):
        res = client.post(f"{V1}/auth/logout-all", headers=auth)
        assert res.status_code == 204
        assert res.content == b""


class TestOpenApi:
    def test_계약의_경로가_전부_열려_있다(self, client):
        paths = set(client.get("/openapi.json").json()["paths"])
        assert paths == {
            "/health",
            f"{V1}/auth/signup",
            f"{V1}/auth/login",
            f"{V1}/auth/google",
            f"{V1}/auth/logout-all",
            f"{V1}/me",
            f"{V1}/me/password",
            f"{V1}/me/card",
            V1 + "/cards/{public_slug}",
            f"{V1}/teams",
            V1 + "/teams/{team_id}",
            V1 + "/teams/{team_id}/members",
            V1 + "/teams/{team_id}/members/{member_id}",
            V1 + "/teams/{team_id}/matches",
            V1 + "/matches/{match_id}",
            V1 + "/matches/{match_id}/applications",
            V1 + "/matches/{match_id}/applications/{application_id}/accept",
            f"{V1}/admin/users",
            V1 + "/admin/users/{user_id}",
        }
