"""card/adapter/inbound/api/v1/card_router.py — 계약 문서 3장."""

from app.card.adapter.outbound.stub.card_stub_repository import DEMO_SLUG
from tests.conftest import V1, error_code


class TestMyCard:
    def test_내_카드(self, client, auth):
        res = client.get(f"{V1}/me/card", headers=auth)
        assert res.status_code == 200
        assert res.json()["public_slug"] == DEMO_SLUG

    def test_인증이_필요하다(self, client):
        res = client.get(f"{V1}/me/card")
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    def test_카드가_없는_사용자면_404(self, client):
        forged = "Bearer stub-token-for-00000000-0000-4000-8000-000000000000"
        res = client.get(f"{V1}/me/card", headers={"Authorization": forged})
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"


class TestPublicCard:
    def test_인증_없이_보인다(self, client):
        assert client.get(f"{V1}/cards/{DEMO_SLUG}").status_code == 200

    def test_내부_id_가_없다(self, client):
        assert "id" not in client.get(f"{V1}/cards/{DEMO_SLUG}").json()

    def test_호칭이_최신순으로_나온다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert [t["code"] for t in titles] == ["sharp_shooter", "weekend_regular"]

    def test_호칭_분류는_부록_D_의_값이다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert {t["category"] for t in titles} <= {"강점", "활동", "용병"}

    def test_시각은_Z_로_끝난다(self, client):
        titles = client.get(f"{V1}/cards/{DEMO_SLUG}").json()["titles"]
        assert all(t["granted_at"].endswith("Z") for t in titles)

    def test_없는_슬러그면_404(self, client):
        res = client.get(f"{V1}/cards/no-such-slug")
        assert res.status_code == 404
        assert error_code(res) == "CARD_NOT_FOUND"
