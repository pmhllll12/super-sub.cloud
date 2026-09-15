"""user/adapter/inbound/api/v1/user_search_router.py — 계약 문서 3-12절."""

from __future__ import annotations

from tests.conftest import V1


class TestSearchUsers:
    def test_인증_없으면_401(self, client):
        res = client.get(f"{V1}/users/search", params={"q": "김"})
        assert res.status_code == 401

    def test_결과가_배열이다(self, client, auth):
        """스텁은 본인을 항상 제외하므로 빈 배열이 정상 응답 형태다."""
        res = client.get(f"{V1}/users/search", params={"q": "아무나"}, headers=auth)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_q_가_없으면_422(self, client, auth):
        res = client.get(f"{V1}/users/search", headers=auth)
        assert res.status_code == 422
