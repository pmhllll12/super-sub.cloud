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


class TestSearchCardSlug:
    """닉네임 검색 결과에도 카드 슬러그가 실린다 (미결 `paik` 39번).

    지인 목록과 **같은 모양**이어야 한다 — 두 자리가 갈리면 화면이 어느
    쪽에서 왔는지에 따라 다르게 짜인다.
    """

    def test_칸이_응답_모양에_있다(self, client, auth):
        res = client.get(f"{V1}/users/search", params={"q": "아무나"}, headers=auth)
        assert res.status_code == 200
        for row in res.json():
            assert "card_public_slug" in row
