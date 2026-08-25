"""user/adapter/inbound/api/v1/me_router.py — 계약 문서 2장."""

import pytest

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
