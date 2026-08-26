"""user/adapter/inbound/api/v1/me_router.py — 계약 문서 2장."""

from uuid import UUID

import pytest

from app.core.security import issue_access_token
from tests.conftest import V1, error_code


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
        [
            "Bearer garbage",
            # JWT 모양인데 서명만 틀렸다. 앞의 "garbage" 와 다른 경로를 지난다 —
            # 이쪽은 디코드까지 가서 서명 검증에서 걸린다.
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ4In0.bogus",
            "Basic abc",
        ],
        ids=["형식아님", "서명틀림", "Bearer아님"],
    )
    def test_토큰이_무효하면_401(self, client, header):
        res = client.get(f"{V1}/me", headers={"Authorization": header})
        assert res.status_code == 401
        assert error_code(res) in {"UNAUTHORIZED", "INVALID_TOKEN"}

    def test_없는_사용자의_토큰이면_INVALID_TOKEN(self, client):
        """**서명은 진짜인데 그 id 의 사용자가 없는** 경우다.

        예전에는 `stub-token-for-<uuid>` 를 적어 넣었는데, 지금은 그게 서명 검증에서
        먼저 걸린다 — 즉 **이름과 다른 이유로 통과하고 있었다.** 실제로 발급한
        토큰을 써야 "사용자 없음" 경로를 지나간다.
        """
        token = issue_access_token(UUID("00000000-0000-4000-8000-000000000000"))
        res = client.get(f"{V1}/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert error_code(res) == "INVALID_TOKEN"


class TestUpdateMe:
    """`PATCH /me` — 계약 문서 2장.

    저장이 실제로 되는지는 스텁으로 확인할 수 없다. 그건 `@pytest.mark.db` 가
    붙은 통합 테스트가 본다. 여기서는 **계약**(응답 형태·에러 코드)만 본다.
    """

    def test_응답이_GET_me_와_같은_형태다(self, client, auth):
        res = client.patch(f"{V1}/me", json={"nickname": "새이름"}, headers=auth)
        assert res.status_code == 200
        assert set(res.json()) == set(client.get(f"{V1}/me", headers=auth).json())

    def test_바뀐_닉네임을_돌려준다(self, client, auth):
        res = client.patch(f"{V1}/me", json={"nickname": "새이름"}, headers=auth)
        assert res.json()["nickname"] == "새이름"

    def test_앞뒤_공백은_정규화된다(self, client, auth):
        res = client.patch(f"{V1}/me", json={"nickname": "  새이름  "}, headers=auth)
        assert res.json()["nickname"] == "새이름"

    def test_헤더가_없으면_UNAUTHORIZED(self, client):
        res = client.patch(f"{V1}/me", json={"nickname": "새이름"})
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    @pytest.mark.parametrize(
        "nickname",
        ["", "가" * 21],
        ids=["빈값", "상한초과"],
    )
    def test_길이가_안_맞으면_422(self, client, auth, nickname):
        res = client.patch(f"{V1}/me", json={"nickname": nickname}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"
