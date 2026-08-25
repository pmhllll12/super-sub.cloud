"""계약 문서의 모든 경로를 성공·실패 양쪽으로 눌러본다.

예전 `smoke.sh`를 옮긴 것이다. 셸 대신 TestClient 를 쓰므로 포트를 잡지 않고
훨씬 빠르며, 응답을 문자열이 아니라 구조로 본다.

**엔드포인트를 추가하면 성공 1건 + 실패 최소 1건을 같이 넣는다.** 이 규칙이 실제로
버그를 잡았다 — 에러 핸들러가 통째로 깨져 모든 실패가 500 이 된 적이 있다.
"""

import pytest
from fastapi.testclient import TestClient

from app.cards.stub_repository import DEMO_SLUG
from app.identity.stub_repository import DEMO_EMAIL, DEMO_PASSWORD
from app.main import app

V1 = "/api/v1"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    res = client.post(
        f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _error_code(res) -> str:
    """계약의 에러 봉투에서 code 를 꺼낸다. 형태가 다르면 여기서 터진다."""
    body = res.json()
    assert set(body) == {"error"}, f"에러 봉투가 아니다: {body}"
    assert set(body["error"]) == {"code", "message"}
    return body["error"]["code"]


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
        # normalize_email 이 경로에 실제로 걸려 있는지 확인한다.
        res = client.post(
            f"{V1}/auth/login",
            json={"email": DEMO_EMAIL.upper(), "password": DEMO_PASSWORD},
        )
        assert res.status_code == 200

    def test_비밀번호가_틀리면_401(self, client):
        res = client.post(
            f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": "wrong-password"}
        )
        assert res.status_code == 401
        assert _error_code(res) == "INVALID_CREDENTIALS"

    def test_없는_계정도_같은_code_를_준다(self, client):
        # 구분하면 가입 여부가 새어 나간다.
        res = client.post(
            f"{V1}/auth/login",
            json={"email": "nobody@example.com", "password": "whatever12"},
        )
        assert res.status_code == 401
        assert _error_code(res) == "INVALID_CREDENTIALS"


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
            json={
                "email": DEMO_EMAIL,
                "password": "password123",
                "nickname": "홍길동",
            },
        )
        assert res.status_code == 409
        assert _error_code(res) == "EMAIL_ALREADY_EXISTS"

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
        assert _error_code(res) == "VALIDATION_ERROR"


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
        # 계약 문서가 RFC 3339 의 'Z' 표기로 적혀 있다.
        assert client.get(f"{V1}/me", headers=auth).json()["created_at"].endswith("Z")

    def test_헤더가_없으면_UNAUTHORIZED(self, client):
        res = client.get(f"{V1}/me")
        assert res.status_code == 401
        assert _error_code(res) == "UNAUTHORIZED"

    def test_토큰이_무효하면_INVALID_TOKEN(self, client):
        # 클라이언트 동작이 다르므로 위와 code 를 나눈다.
        res = client.get(f"{V1}/me", headers={"Authorization": "Bearer garbage"})
        assert res.status_code == 401
        assert _error_code(res) == "INVALID_TOKEN"


class TestCards:
    def test_내_카드(self, client, auth):
        res = client.get(f"{V1}/me/card", headers=auth)
        assert res.status_code == 200
        assert res.json()["public_slug"] == DEMO_SLUG

    def test_내_카드는_인증이_필요하다(self, client):
        res = client.get(f"{V1}/me/card")
        assert res.status_code == 401
        assert _error_code(res) == "UNAUTHORIZED"

    def test_공개_카드는_인증_없이_보인다(self, client):
        res = client.get(f"{V1}/cards/{DEMO_SLUG}")
        assert res.status_code == 200

    def test_공개_카드에_내부_id_가_없다(self, client):
        assert "id" not in client.get(f"{V1}/cards/{DEMO_SLUG}").json()

    def test_호칭이_최신순으로_나온다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert [t["code"] for t in titles] == ["sharp_shooter", "weekend_regular"]

    def test_없는_슬러그면_404(self, client):
        res = client.get(f"{V1}/cards/no-such-slug")
        assert res.status_code == 404
        assert _error_code(res) == "CARD_NOT_FOUND"


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
