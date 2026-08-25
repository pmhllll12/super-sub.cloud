"""user 컨텍스트의 HTTP 경계. 계약 문서 2장.

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다.** 이 규칙이 실제로
버그를 잡았다 — 에러 핸들러가 통째로 깨져 모든 실패가 500 이 된 적이 있다.
"""

import pytest

from app.user.adapter.outbound.stub_repository import DEMO_EMAIL, DEMO_PASSWORD
from tests.conftest import V1, error_code


class TestHealth:
    def test_기동(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["stub"] is True


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
        res = client.post(f"{V1}/auth/login", json={"email": email, "password": password})
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


class TestMe:
    def test_토큰이_있으면_내_정보를_준다(self, client, auth):
        res = client.get(f"{V1}/me", headers=auth)
        assert res.status_code == 200
        assert res.json()["nickname"] == "홍길동"

    def test_탈퇴한_팀은_안_나온다(self, client, auth):
        # 스텁에 나간 팀이 하나 들어 있다. 거르지 않으면 여기서 잡힌다.
        teams = client.get(f"{V1}/me", headers=auth).json()["teams"]
        assert [t["name"] for t in teams] == ["번개FC"]

    def test_시각은_Z_로_끝난다(self, client, auth):
        assert client.get(f"{V1}/me", headers=auth).json()["created_at"].endswith("Z")

    def test_헤더가_없으면_UNAUTHORIZED(self, client):
        res = client.get(f"{V1}/me")
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    @pytest.mark.parametrize(
        "header",
        ["Bearer garbage", "Bearer stub-token-for-not-a-uuid", "Basic abc"],
        ids=["형식아님", "uuid아님", "Bearer아님"],
    )
    def test_토큰이_무효하면_401(self, client, header):
        res = client.get(f"{V1}/me", headers={"Authorization": header})
        assert res.status_code == 401
        assert error_code(res) in {"UNAUTHORIZED", "INVALID_TOKEN"}

    def test_없는_사용자의_토큰이면_INVALID_TOKEN(self, client):
        # 토큰 형식은 맞지만 그 id 의 사용자가 없다.
        forged = "Bearer stub-token-for-00000000-0000-4000-8000-000000000000"
        res = client.get(f"{V1}/me", headers={"Authorization": forged})
        assert res.status_code == 401
        assert error_code(res) == "INVALID_TOKEN"


class TestOpenApi:
    def test_계약의_경로가_전부_열려_있다(self, client):
        paths = set(client.get("/openapi.json").json()["paths"])
        assert paths == {
            "/health",
            f"{V1}/auth/signup",
            f"{V1}/auth/login",
            f"{V1}/me",
            f"{V1}/me/card",
            V1 + "/cards/{public_slug}",
        }
